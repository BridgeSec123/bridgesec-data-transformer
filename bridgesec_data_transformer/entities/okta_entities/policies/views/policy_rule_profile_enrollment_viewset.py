import logging

import requests
from core.utils.pagination import fetch_all_pages
from core.utils.rate_limit import handle_rate_limit, rate_limit_headers
from django.conf import settings

from entities.okta_entities.policies.policy_models import PolicyRuleProfileEnrollment
from entities.okta_entities.policies.policy_serializers import (
    PolicyRuleProfileEnrollmentSerializer,
)
from entities.okta_entities.policies.views.policy_base_viewset import BasePolicyViewSet

logger = logging.getLogger(__name__)


class PolicyRuleProfileEnrollmentViewSet(BasePolicyViewSet):
    okta_endpoint = "/api/v1/policies/{policy_id}/rules"
    entity_type = "okta_policy_rule_profile_enrollment"
    serializer_class = PolicyRuleProfileEnrollmentSerializer
    model = PolicyRuleProfileEnrollment
    
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
            profile_attributes = record.get("actions", {}).get("profileEnrollment", {})
            formatted_record = {
                "policy_id": policy_id,
                "unknown_user_action": profile_attributes.get("unknownUserAction", ""),
                "access": profile_attributes.get("access", ""),
                "email_verification": profile_attributes.get("activationRequirements", {}).get("emailVerification"),
                "enroll_authenticator_types": profile_attributes.get("enrollment", {}).get("authenticatorEnrollments", []),
                "inline_hook_id": profile_attributes.get("inlineHookId", ""),
                "profile_attributes": [
                    {
                        "name": attr.get("name", ""),
                        "label": attr.get("label", ""),
                        "required": attr.get("required", False)
                    }
                    for attr in profile_attributes.get("profileAttributes", [])
                ],
                "progressive_profiling_action": profile_attributes.get("progressiveProfilingAction", ""),
                "target_group_id": profile_attributes.get("targetGroupIds", ""),
                "ui_schema_id": profile_attributes.get("uiSchemaId", "")
            }
            formatted_data.append(formatted_record)

        logger.info("Final extracted %d user records after formatting and filtering", len(formatted_data))
        return formatted_data
