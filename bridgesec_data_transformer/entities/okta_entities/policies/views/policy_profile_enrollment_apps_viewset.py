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
        Override to extract app names by fetching app details for each app ID.
        """
        logger.info("Extracting data from Okta response")
        extracted_data = super().extract_data(okta_data)

        # Fetch app details for each app ID to get the name
        # app_names = []
        # headers = {"Authorization": f"SSWS {settings.OKTA_API_TOKEN}"}

        formatted_data = []
        for record in extracted_data:
            app_id = record.get("id", "")
            # if app_id:
            #     # Fetch app details
            #     app_url = f"{settings.OKTA_API_URL}/api/v1/apps/{app_id}"
            #     try:
            #         response = requests.get(app_url, headers=headers)
            #         if response.status_code == 200:
            #             app_data = response.json()
            #             app_name = app_data.get("label") or app_data.get("name", "")
            #             if app_name:
            #                 app_names.append(app_name)
            #         else:
            #             logger.warning(f"Failed to fetch app details for ID {app_id}")
            #             # Fallback to ID if we can't get the name
            #             app_names.append(app_id)
            #     except Exception as e:
            #         logger.error(f"Error fetching app details for ID {app_id}: {e}")
            #         app_names.append(app_id)

            formatted_data.append({
                "policy_id": policy_profile_enrollment_id,
                "app_id": app_id
            })
        logger.info("Final extracted %d Policy records after formatting and filtering", len(formatted_data))
        return formatted_data
