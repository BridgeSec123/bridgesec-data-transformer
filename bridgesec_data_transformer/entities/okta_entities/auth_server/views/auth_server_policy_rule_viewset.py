import logging

import requests
from django.conf import settings

from entities.okta_entities.auth_server.auth_server_models import (
    AuthorizationServerPolicyRule,
)
from entities.okta_entities.auth_server.auth_server_serializers import (
    AuthorizationServerPolicyRuleSerializer,
)
from entities.okta_entities.auth_server.views.auth_server_base_viewset import (
    BaseAuthServerViewSet,
)

logger = logging.getLogger(__name__)

class AuthorizationServerPolicyRuleViewSet(BaseAuthServerViewSet):
    model = AuthorizationServerPolicyRule
    serializer_class = AuthorizationServerPolicyRuleSerializer
    okta_endpoint = "api/v1/authorizationServers/{auth_server_id}/policies/{policy_id}/rules"
    entity_type = "auth_server_policy_rules"

    def fetch_from_okta(self, auth_server_id, policy_id):
        if not auth_server_id or not policy_id:
            logger.error("Both Auth Server ID and Policy ID are required to fetch policy rules.")
            return []

        url = f"{settings.OKTA_API_URL}/{self.okta_endpoint.format(auth_server_id=auth_server_id, policy_id=policy_id)}"
        headers = {"Authorization": f"SSWS {settings.OKTA_API_TOKEN}"}

        logger.info(f"Fetching policy rules from Okta API: {url}")
        response = requests.get(url, headers=headers)

        content = response.text.strip()
        if response.status_code == 200:
            if content:
                try:
                    return response.json()
                except Exception as e:
                    logger.error(f"Failed to decode JSON response: {e}")
                    return []
            else:
                logger.warning(f"Empty response received for {auth_server_id}/{policy_id}")
                return []
        else:
            logger.error(f"Failed to fetch policy rules for auth server. Status: {response.status_code}, Response: {content}")
            return []

    def extract_data(self, okta_data, auth_server_id, policy_id):
        extracted_data = []
        for rule in okta_data:
            record = {
                "auth_server_id": auth_server_id,
                "policy_id": policy_id,
                "name": rule.get("name"),
                "priority": rule.get("priority"),
                "grant_type_whitelist": rule.get("conditions", {}).get("grantTypes", {}).get("include", []),
                "group_blacklist": rule.get("conditions", {}).get("people", {}).get("groups", {}).get("exclude", []),
                "group_whitelist": rule.get("conditions", {}).get("people", {}).get("groups", {}).get("include", []),
                "user_blacklist": rule.get("conditions", {}).get("people", {}).get("users", {}).get("exclude", []),
                "user_whitelist": rule.get("conditions", {}).get("people", {}).get("users", {}).get("include", []),
                "scope_whitelist": rule.get("conditions", {}).get("scopes", {}).get("include", []),
                "inline_hook_id": rule.get("actions", {}).get("token", {}).get("inlineHook", {}).get("id"),
                "access_token_lifetime_minutes": rule.get("actions", {}).get("token", {}).get("accessTokenLifetimeMinutes", ""),
                "refresh_token_lifetime_minutes": rule.get("actions", {}).get("token", {}).get("refreshTokenLifetimeMinutes", ""),
                "refresh_token_window_minutes": rule.get("actions", {}).get("token", {}).get("refreshTokenWindowMinutes", ""),
                "type": rule.get("type"),
                "status": rule.get("status"),
            }
            extracted_data.append(record)

        logger.info(f"Extracted {len(extracted_data)} auth server policy rule records.")
        return extracted_data
