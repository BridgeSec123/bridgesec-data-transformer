import logging

import requests
from core.utils.pagination import fetch_all_pages
from core.utils.rate_limit import handle_rate_limit, rate_limit_headers
from django.conf import settings

from entities.okta_entities.policies.policy_models import PolicyRuleSignOn
from entities.okta_entities.policies.policy_serializers import (
    PolicyRuleSignOnSerializer,
)
from entities.okta_entities.policies.views.policy_base_viewset import BasePolicyViewSet

logger = logging.getLogger(__name__)

class PolicyRuleSignOnViewSet(BasePolicyViewSet):
    okta_endpoint = "/api/v1/policies/{policy_id}/rules"
    entity_type = "okta_policy_rule_signon"
    serializer_class = PolicyRuleSignOnSerializer
    model = PolicyRuleSignOn
    
    def fetch_from_okta(self, policy_id):
        """Fetch data from Okta API dynamically."""
        if not self.okta_endpoint:
            logger.error("Okta endpoint not defined")
            return {"error": "Okta endpoint not defined"}, 500

        okta_url = f"{settings.OKTA_API_URL}/{self.okta_endpoint.format(policy_id=policy_id)}"
        headers = {"Authorization": f"SSWS {settings.OKTA_API_TOKEN}"}
        
        logger.info(f"Fetching data from Okta endpoint: {self.okta_endpoint}")
        
        while True:  # Keep retrying if rate limited
            response = requests.get(okta_url, headers=headers)

            if handle_rate_limit(response):  # Handle rate limit
                logger.warning("Rate limit reached. Retrying...")
                continue  # Retry after waiting

            if response.status_code != 200:
                logger.error(f"Failed to fetch data from Okta: {response.text}")
                return {"error": f"Failed to fetch data from Okta API: {response.text}"}, response.status_code, rate_limit_headers(response)

            response_data = response.json()
            logger.info(f"Successfully fetched data from Okta ({len(response_data)} records)")
            
            # Check if pagination is needed
            next_url = response.links.get("next", {}).get("url")
            if next_url:
                all_data = fetch_all_pages(okta_url, headers)
                return all_data, 200, rate_limit_headers(response)

            return response_data, 200, rate_limit_headers(response)

    def extract_data(self, okta_data, policy_id):
        """
        Override to format the user data by removing the "profile" key.
        """
        logger.info("Extracting data from Okta response")
        extracted_data = super().extract_data(okta_data)

        formatted_data = []

        for record in extracted_data:
            actions = record.get("actions")
            signon = actions.get("signon")
            conditions = record.get("conditions")
            session = signon.get("session")
            formatted_record = {
                "name": record.get("name", ""),
                "access": signon.get("access", ""),
                "auth_type": conditions.get("authContext").get("authType"),
                "behaviors": conditions.get("behaviors"),
                "factor_sequence": conditions.get("factorSequence", {}),
                "identity_provider": conditions.get("identityProvider", ""),
                "identity_provider_ids": conditions.get("identityProvider", {}).get("id"),
                "mfa_prompt": signon.get("mfa", {}).get("prompt"),
                "mfa_lifetime": signon.get("mfa", {}).get("rememberDeviceLifetime"),
                "mfa_remember_device": signon.get("mfa", {}).get("rememberDevice"),
                "mfa_required": signon.get("mfa", {}).get("required"),
                "network_connection": conditions.get("network", {}).get("connection"),
                "network_excludes": conditions.get("network", {}).get("exclude", []),
                "network_includes": conditions.get("network", {}).get("include", []),
                "policy_id": policy_id,
                "primary_factor": signon.get("primaryFactor", {}),
                "priority": record.get("priority"),
                "risk_level": signon.get("risk", ""),
                "session_idle": session.get("maxSessionIdleMinutes"),
                "session_lifetime": session.get("maxSessionLifetimeMinutes"),
                "session_persistent": session.get("usePersistentCookie"),
                "status": record.get("status"),
                "users_excluded": conditions.get("people", {}).get("users", {}).get("exclude", []),
            }
            formatted_data.append(formatted_record)

        logger.info("Final extracted %d user records after formatting and filtering", len(formatted_data))
        return formatted_data
