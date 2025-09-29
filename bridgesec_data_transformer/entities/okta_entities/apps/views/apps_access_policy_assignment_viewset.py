import logging
import requests

from entities.okta_entities.apps.apps_models import AppAccessPolicyAssignment
from entities.okta_entities.apps.apps_serializers import (
    AppAccessPolicyAssignmentSerializer,
)
from entities.okta_entities.apps.views.apps_base_viewset import BaseAppViewSet
from django.conf import settings
from core.utils.rate_limit import handle_rate_limit, rate_limit_headers

logger = logging.getLogger(__name__)


class AppAccessPolicyAssignmentViewSet(BaseAppViewSet):
    okta_endpoint = "/api/v1/apps"
    entity_type = "apps_access_policy_assignment"
    serializer_class = AppAccessPolicyAssignmentSerializer
    model = AppAccessPolicyAssignment

    def get_policy_name(self, policy_id):
        """
        Fetch policy name from Okta API using policy_id.
        """
        try:
            okta_url = f"{settings.OKTA_API_URL}/api/v1/policies/{policy_id}"
            headers = {"Authorization": f"SSWS {settings.OKTA_API_TOKEN}"}

            while True:  # Keep retrying if rate limited
                response = requests.get(okta_url, headers=headers)

                if handle_rate_limit(response):  # Handle rate limit
                    logger.warning("Rate limit reached. Retrying...")
                    continue  # Retry after waiting

                if response.status_code != 200:
                    logger.error(f"Failed to fetch policy {policy_id}: {response.text}")
                    return policy_id  # Return original policy_id if API call fails

                policy_data = response.json()
                policy_name = policy_data.get("name", policy_id)
                logger.info(f"Mapped policy_id {policy_id} to policy_name '{policy_name}'")
                return policy_name

        except Exception as e:
            logger.error(f"Error fetching policy name for {policy_id}: {e}")
            return policy_id  # Return original policy_id if error occurs

    def extract_data(self, okta_data):
        """
        Extract access policy info from apps.
        """
        formatted_data = []

        for app in okta_data:
            app_id = app.get("label")
            access_policy_url = app.get("_links", {}).get("accessPolicy", {}).get("href")

            if not access_policy_url:
                logger.info(f"No access policy found for app {app_id}. Skipping.")
                continue

            try:
                policy_id = access_policy_url.rstrip("/").split("/")[-1]
            except Exception as e:
                logger.error(f"Failed to extract policy ID from {access_policy_url}: {e}")
                continue

            # Get policy name using the policy_id
            policy_name = self.get_policy_name(policy_id)

            formatted_record = {
                "app_id": app_id,
                "policy_id": policy_name
            }
            formatted_data.append(formatted_record)

        logger.info("Final extracted %d policy assignment records", len(formatted_data))
        return formatted_data
