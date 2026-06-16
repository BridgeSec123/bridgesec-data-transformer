import logging

import requests
from core.utils.okta_helpers import get_okta_headers
from core.utils.pagination import fetch_all_pages
from core.utils.rate_limit import handle_rate_limit
from django.conf import settings

from entities.okta_entities.entity_risk_policy.entity_risk_policy_models import EntityRiskPolicyRule
from entities.okta_entities.entity_risk_policy.entity_risk_policy_serializers import EntityRiskPolicyRuleSerializer
from entities.views.base_view import BaseEntityViewSet

logger = logging.getLogger(__name__)


class EntityRiskPolicyRuleViewSet(BaseEntityViewSet):
    okta_endpoint = "api/v1/policies/{policy_id}/rules"
    entity_type = "okta_entity_risk_policy_rule"
    serializer_class = EntityRiskPolicyRuleSerializer
    model = EntityRiskPolicyRule

    def fetch_from_okta(self, policy_id, request=None):
        if not policy_id:
            logger.error("policy_id is required to fetch entity risk policy rules.")
            return []

        okta_url = f"{self.okta_base_url}/{self.okta_endpoint.format(policy_id=policy_id)}"
        headers = get_okta_headers(request)

        while True:
            response = requests.get(okta_url, headers=headers)

            if handle_rate_limit(response):
                logger.warning("Rate limit reached fetching entity risk policy rules. Retrying...")
                continue

            if response.status_code == 404:
                logger.debug("No rules found for entity risk policy %s", policy_id)
                return []

            if response.status_code != 200:
                logger.error("Failed to fetch rules for policy %s: %s", policy_id, response.text)
                return []

            response_data = response.json()
            next_url = response.links.get("next", {}).get("url")
            if next_url:
                response_data = fetch_all_pages(okta_url, headers)

            return response_data

    def extract_data(self, okta_data, policy_id):
        items = okta_data if isinstance(okta_data, list) else ([okta_data] if okta_data else [])
        result = []
        for item in items:
            if not isinstance(item, dict):
                continue

            actions = item.get("actions", {}).get("entityRisk", {})
            conditions = item.get("conditions", {})
            people = conditions.get("people", {})
            users = people.get("users", {})
            groups = people.get("groups", {})
            entity_risk_cond = conditions.get("entityRisk", {})

            result.append({
                "policy_rule_id": item.get("id", ""),
                "policy_id": policy_id,
                "name": item.get("name", ""),
                "risk_level": entity_risk_cond.get("riskLevel", ""),
                "status": item.get("status", ""),
                "priority": item.get("priority"),
                "users_included": users.get("include") or [],
                "users_excluded": users.get("exclude") or [],
                "groups_included": groups.get("include") or [],
                "groups_excluded": groups.get("exclude") or [],
                "terminate_all_sessions": actions.get("terminateAllSessions", False),
                "workflow_id": actions.get("workflowId") or "",
            })

        logger.info("Extracted %d entity risk policy rules for policy %s", len(result), policy_id)
        return result
