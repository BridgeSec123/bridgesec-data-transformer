import logging

import requests
from core.utils.pagination import fetch_all_pages
from core.utils.rate_limit import handle_rate_limit, rate_limit_headers
from django.conf import settings

from entities.okta_entities.apps.apps_models import AppPolicySignOnRule
from entities.okta_entities.apps.apps_serializers import AppPolicySignOnRuleSerializer
from entities.okta_entities.apps.views.apps_base_viewset import BaseAppViewSet

logger = logging.getLogger(__name__)

class AppPolicyRuleSignOnViewSet(BaseAppViewSet):
    okta_endpoint = "/api/v1/policies/{policy_id}/rules"
    entity_type = "okta_app_signon_policy_rule"
    serializer_class = AppPolicySignOnRuleSerializer
    model = AppPolicySignOnRule
    
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
            actions = record.get("actions", {})
            appsignon = actions.get("appSignOn", {})
            verificationMethod = appsignon.get("verificationMethod") or {}
            constraints = verificationMethod.get("constraints") or []
            conditions = record.get("conditions") or {}
            formatted_record = {
                "name": record.get("name", ""),
                "policy_id": policy_id,
                "access": appsignon.get("access", ""),
                "constraints": constraints,
                "custom_expression": record.get("customExpression", ""),
                "device_assurances_included": record.get("deviceEnrollments", []),
                "device_is_managed": record.get("isManaged", False),
                "device_is_registered": record.get("isRegistered", False),
                "factor_mode": verificationMethod.get("factorMode", ""),
                "groups_excluded": record.get("groups_excluded", []),
                "groups_included": record.get("groups_included", []),
                "inactivity_period": record.get("inactivityPeriod", ""),
                "network_connection": record.get("network_connection", ""),
                "network_excludes": record.get("network_excludes", []),
                "network_includes": record.get("network_includes", []),
                "platform_include": record.get("platform_include", []),
                "re_authentication_frequency": record.get("reauth", {}).get("frequency", ""),
                "priority": record.get("priority", ""),
                "risk_score": conditions.get("riskScore", ""),
                "status": record.get("status", ""),
                "type": verificationMethod.get("type", ""),
                "user_types_excluded": record.get("userTypes_excluded", []),
                "user_types_included": record.get("userTypes_included", []),
                "users_included": record.get("users_included", []),
                "users_excluded": record.get("users_excluded", []),
            }
            formatted_data.append(formatted_record)

        logger.info("Final extracted %d app policy rule sign on records after formatting and filtering", len(formatted_data))
        return formatted_data
