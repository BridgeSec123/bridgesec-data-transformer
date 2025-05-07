import logging

import requests
from core.utils.pagination import fetch_all_pages
from core.utils.rate_limit import handle_rate_limit, rate_limit_headers
from django.conf import settings

from entities.okta_entities.users.user_models import RoleSubscription
from entities.okta_entities.users.user_serializers import RoleSubscriptionSerializer
from entities.okta_entities.users.views.user_base_viewset import BaseUserViewSet

logger = logging.getLogger(__name__)

class RoleSubscriptionViewSet(BaseUserViewSet):
    okta_endpoint = "api/v1/roles/{role_type}/subscriptions"
    entity_type = "okta_role_subscription"
    serializer_class = RoleSubscriptionSerializer
    model = RoleSubscription

    def fetch_from_okta(self,role_type):
        if not self.okta_endpoint:
            logger.error("Okta endpoint not defined")
            return {"error": "Okta endpoint not defined"}, 500

        okta_url = f"{settings.OKTA_API_URL}/{self.okta_endpoint.format(role_type=role_type)}"
        headers = {"Authorization": f"SSWS {settings.OKTA_API_TOKEN}"}

        logger.info(f"Fetching data from Okta endpoint: {self.okta_endpoint}")

        while True:  # Keep retrying if rate limited
            response = requests.get(okta_url, headers=headers)

            if handle_rate_limit(response):  # Handle rate limit
                logger.warning("Rate limit reached. Retrying...")
                continue  # Retry after waiting
            
            if response.status_code == 400:
                logger.warning(f"400 Bad Request for role_type={role_type}. Returning empty list.")
                return []

            if response.status_code != 200:
                logger.error(f"Failed to fetch data from Okta: {response.text}")
                return {"error": f"Failed to fetch data from Okta API: {response.text}"}, response.status_code, rate_limit_headers(response)

            response_data = response.json()
            logger.info(f"Successfully fetched data from Okta ({len(response_data)} records)")

            # Check if pagination is needed
            next_url = response.links.get("next", {}).get("url")
            if next_url:
                all_data = fetch_all_pages(okta_url, headers)
                return all_data

            return response_data

    def extract_data(self, okta_data, role_type):

        formatted_data = []

        for record in okta_data:
            if not isinstance(record, dict):
                logger.warning(f"Skipping invalid record (not a dict): {record}")
                continue

            formatted_record = {
                "role_type": role_type,
                "notification_type": record.get("notificationType", ""),
                "status": record.get("status", ""),
            }
            formatted_data.append(formatted_record)
        return formatted_data