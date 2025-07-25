import logging

import requests
from core.utils.rate_limit import handle_rate_limit, rate_limit_headers
from django.conf import settings

from entities.okta_entities.apps.apps_models import AppUser
from entities.okta_entities.apps.apps_serializers import AppUserSerializer
from entities.okta_entities.apps.views.apps_base_viewset import BaseAppViewSet

logger = logging.getLogger(__name__)

class AppUserViewSet(BaseAppViewSet):  
    okta_endpoint = "/api/v1/apps"
    entity_type = "okta_app_users"
    serializer_class = AppUserSerializer
    model =  AppUser

    def extract_data(self, okta_data):
        logger.info("Extracting data from Okta response")
        formatted_data = []

        for record in okta_data:
            app_id = record.get("id", "")
            users_url = record.get("_links", {}).get("users", {}).get("href", "")
            user_data = []

            if users_url:
                try:
                    headers = {"Authorization": f"SSWS {settings.OKTA_API_TOKEN}"}

                    # Retry loop for rate limits
                    while True:
                        response = requests.get(users_url, headers=headers)
                        if handle_rate_limit(response):
                            continue
                        response.raise_for_status()
                        break

                    user_data = response.json()

                    if not isinstance(user_data, list):
                        logger.error(f"Unexpected user data format from {users_url}: {type(user_data)}")
                        continue

                except Exception as e:
                    logger.error(f"Failed to fetch users from {users_url}: {e}")
                    continue

                for user in user_data:
                    formatted_record = {
                        "app_id": app_id,
                        "user_id": user.get("id", ""),
                        "password": user.get("password", ""),
                        "profile": user.get("profile", {}),
                        "retain_assignment": user.get("retain_assignment", ""),
                        "username": user.get("credentials", {}).get("userName", "") if user.get("credentials", {}) else ""
                    }
                    formatted_data.append(formatted_record)

        logger.info("Final extracted %d app user records after formatting and flattening", len(formatted_data))
        return formatted_data