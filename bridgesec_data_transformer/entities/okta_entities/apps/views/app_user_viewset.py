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

    def get_user_name(self, user_id):
        """
        Fetch user name from Okta API using user_id.
        """
        try:
            okta_url = f"{settings.OKTA_API_URL}/api/v1/users/{user_id}"
            headers = {"Authorization": f"SSWS {settings.OKTA_API_TOKEN}"}

            while True:  # Keep retrying if rate limited
                response = requests.get(okta_url, headers=headers)

                if handle_rate_limit(response):  # Handle rate limit
                    logger.warning("Rate limit reached. Retrying...")
                    continue  # Retry after waiting

                if response.status_code != 200:
                    logger.error(f"Failed to fetch user {user_id}: {response.text}")
                    return user_id  # Return original user_id if API call fails

                user_data = response.json()
                # Try to get display name, or fall back to email or login
                user_name = user_data.get("profile", {}).get("firstName") or \
                           user_data.get("profile", {}).get("email") or \
                           user_data.get("profile", {}).get("login") or \
                           user_id
                logger.info(f"Mapped user_id {user_id} to user_name '{user_name}'")
                return user_name

        except Exception as e:
            logger.error(f"Error fetching user name for {user_id}: {e}")
            return user_id  # Return original user_id if error occurs

    def extract_data(self, okta_data):
        logger.info("Extracting data from Okta response")
        formatted_data = []

        for record in okta_data:
            app_id = record.get("label", "")  # <-- get app label
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
                    # Extract user_id from the user data
                    user_id = user.get("id", "")

                    # Get user name using the user_id
                    user_name = self.get_user_name(user_id) if user_id else ""

                    formatted_record = {
                        "app_id": app_id,      # <-- use label if available
                        "user_id": user_name,               # <-- use user name instead of user_id
                        "password": user.get("password", ""),
                        "profile": user.get("profile", {}),
                        "retain_assignment": user.get("retain_assignment", ""),
                        "username": user.get("credentials", {}).get("userName", "") if user.get("credentials", {}) else ""
                    }
                    formatted_data.append(formatted_record)

        logger.info("Final extracted %d app user records after formatting and flattening", len(formatted_data))
        return formatted_data