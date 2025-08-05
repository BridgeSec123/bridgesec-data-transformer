import logging

import requests
from core.utils.rate_limit import handle_rate_limit, rate_limit_headers
from django.conf import settings

from entities.okta_entities.policies.policy_models import PolicyRuleIDPDiscovery
from entities.okta_entities.policies.policy_serializers import (
    PolicyRuleIDPDiscoverySerializer,
)
from entities.okta_entities.policies.views.policy_base_viewset import BasePolicyViewSet

logger = logging.getLogger(__name__)

class PolicyRuleIDPDiscoveryViewSet(BasePolicyViewSet):
    okta_endpoint = "/api/v1/policies/{policy_id}/rules"
    entity_type = "okta_policy_rule_idp_discovery"
    serializer_class = PolicyRuleIDPDiscoverySerializer
    model = PolicyRuleIDPDiscovery
    
    def fetch_from_okta(self, _=None):
        """
        Fetch IDP_DISCOVERY policies and their rules, attaching policy_id to each rule.
        """
        discovery_url = f"{settings.OKTA_API_URL}/api/v1/policies"
        headers = {"Authorization": f"SSWS {settings.OKTA_API_TOKEN}"}
        params = {"type": "IDP_DISCOVERY"}

        logger.info("Fetching IDP_DISCOVERY policies from Okta.")

        response = requests.get(discovery_url, headers=headers, params=params)
        if handle_rate_limit(response):
            logger.warning("Rate limit hit while fetching IDP_DISCOVERY policies.")
            return {"error": "Rate limit hit."}, 429, rate_limit_headers(response)

        if response.status_code != 200:
            logger.error(f"Failed to fetch IDP_DISCOVERY policies: {response.text}")
            return {"error": f"Failed to fetch policies: {response.text}"}, response.status_code, rate_limit_headers(response)

        policies = response.json()
        all_rules = []

        logger.info(f"Found {len(policies)} IDP_DISCOVERY policies. Fetching rules...")

        for policy in policies:
            policy_id = policy.get("id")
            if not policy_id:
                logger.warning("Policy without ID found. Skipping.")
                continue

            rules_url = f"{settings.OKTA_API_URL}/api/v1/policies/{policy_id}/rules"
            rule_response = requests.get(rules_url, headers=headers)

            if handle_rate_limit(rule_response):
                logger.warning(f"Rate limit hit while fetching rules for policy {policy_id}.")
                continue

            if rule_response.status_code != 200:
                logger.error(f"Failed to fetch rules for policy {policy_id}: {rule_response.text}")
                continue

            rules_data = rule_response.json()
            
            # Add policy_id to each rule
            for rule in rules_data:
                rule["policy_id"] = policy_id
                all_rules.append(rule)

            logger.info(f"Fetched {len(rules_data)} rules for policy {policy_id}")

        return all_rules, 200, rate_limit_headers(response)
    
    def extract_data(self, okta_data):
        """
        Override to format the user data by removing the "profile" key.
        """
        logger.info("Extracting data from Okta response")
        extracted_data = super().extract_data(okta_data)

        formatted_data = []

        for record in extracted_data:
            conditions = record.get("conditions")
            actions = record.get("actions")
            formatted_record = {
                "name": record.get("name"),
                "policy_id": record.get("policy_id"),
                "app_exclude": conditions.get("app").get("exclude", []),
                "app_include": conditions.get("app").get("include", []),
                "idp_id": actions.get("idp").get("providers")[0].get("type", []),
                "idp_type": actions.get("idp").get("providers")[0].get("type", []),
                "network_connection": conditions.get("network").get("connection",[]),
                "network_excludes": record.get("network_excludes",[]),
                "network_includes": record.get("network_includes",[]),
                "platform_include": conditions.get("platform").get("include"), 
                "priority": record.get("priority"),
                "status": record.get("status"),
                "user_identifier_attribute": conditions.get("userIdentifier").get("attribute",""),
                "user_identifier_patterns": conditions.get("userIdentifier").get("patterns", []),
                "user_identifier_type": conditions.get("userIdentifier").get("type", [])
            }
            formatted_data.append(formatted_record)

        logger.info("Final extracted %d user records after formatting and filtering", len(formatted_data))
        return formatted_data
