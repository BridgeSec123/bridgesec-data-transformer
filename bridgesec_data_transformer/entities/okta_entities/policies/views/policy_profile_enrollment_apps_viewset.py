import logging

import requests
from core.utils.pagination import fetch_all_pages
from core.utils.rate_limit import handle_rate_limit, rate_limit_headers
from django.conf import settings

from entities.okta_entities.policies.policy_models import PolicyProfileEnrollmentApps
from entities.okta_entities.policies.policy_serializers import (
    PolicyProfileEnrollmentAppsSerializer,
)
from entities.okta_entities.policies.views.policy_base_viewset import BasePolicyViewSet

logger = logging.getLogger(__name__)


class PolicyProfileEnrollmentAppsViewSet(BasePolicyViewSet):
    okta_endpoint = "/api/v1/policies/{policyProfileEnrollmentId}/app"
    entity_type = "okta_policy_profile_enrollment_apps"
    serializer_class = PolicyProfileEnrollmentAppsSerializer
    model = PolicyProfileEnrollmentApps
    
    def fetch_from_okta(self, policy_profile_enrollment_id):
        """Fetch data from Okta API dynamically."""
        if not self.okta_endpoint:
            logger.error("Okta endpoint not defined")
            return {"error": "Okta endpoint not defined"}, 500

        okta_url = f"{settings.OKTA_API_URL}/{self.okta_endpoint.format(policyProfileEnrollmentId=policy_profile_enrollment_id)}"
        headers = {"Authorization": f"SSWS {settings.OKTA_API_TOKEN}"}
        
        params = {
            "type": "PROFILE_ENROLLMENT"
        }
        
        logger.info(f"Fetching data from Okta endpoint: {self.okta_endpoint}")
        
        while True:  # Keep retrying if rate limited
            response = requests.get(okta_url, headers=headers, params=params)

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
    
    def extract_data(self, okta_data, policy_profile_enrollment_id):
        """
        Override to format the user data by removing the "profile" key.
        """
        logger.info("Extracting data from Okta response")
        extracted_data = super().extract_data(okta_data)

        apps = [record.get("id", "") for record in extracted_data if "id" in record]
        formatted_data = [{
            "policy_id": policy_profile_enrollment_id,
            "apps": apps
        }]
        logger.info("Final extracted %d Policy records after formatting and filtering", len(formatted_data))
        return formatted_data
