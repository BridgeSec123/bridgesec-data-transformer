import logging

import requests
from core.utils.rate_limit import handle_rate_limit, rate_limit_headers
from django.conf import settings
from entities.okta_entities.apps.apps_models import AppUser
from entities.okta_entities.apps.apps_serializers import AppUserSerializer
from entities.okta_entities.apps.views.apps_base_viewset import BaseAppViewSet

logger = logging.getLogger(__name__)

class AppUserViewSet(BaseAppViewSet):
    okta_endpoint = "/api/v1/apps/{appId}/users"
    entity_type = "okta_app_users"
    serializer_class = AppUserSerializer
    model = AppUser

    def fetch_from_okta(self, app_id):
        """
        Fetch users for a specific app from Okta.
        """
        base_url = settings.OKTA_API_URL
        headers = {"Authorization": f"SSWS {settings.OKTA_API_TOKEN}"}

        # API call to get users for this app
        users_url = f"{base_url}/api/v1/apps/{app_id}/users"
        logger.info(f"Fetching users for app_id: {app_id}")

        response = requests.get(users_url, headers=headers)

        if handle_rate_limit(response):
            logger.warning(f"Rate limit hit for app_id: {app_id}")
            return {"error": "Rate limit hit."}, 429, rate_limit_headers(response)

        if response.status_code != 200:
            logger.error(f"Failed to fetch users for app {app_id}: {response.text}")
            return {"error": f"Failed to fetch users: {response.text}"}, response.status_code, rate_limit_headers(response)

        user_data = response.json()
        logger.info(f"Fetched {len(user_data)} users for app_id: {app_id}")

        return user_data, 200, rate_limit_headers(response)

    def extract_data(self, okta_data, app=None):
        """
        Formats user data.
        """
        if not app:
            logger.warning("No app info provided for formatting")
            return []
        app_id = app.get("app_id")
        formatted_users = []
        for user in okta_data:
            credentials = user.get("credentials", {})
            formatted_users.append({
                "app_id": app_id,
                "user_id": user.get("id", ""),
                "password": user.get("password", ""),
                "profile": user.get("profile", {}),
                "retain_assignment": user.get("retain_assignment", ""),
                "username": credentials.get("userName", "") if credentials else ""
            })

        logger.info(f"Formatted {len(formatted_users)} users for app: {app_id}")
        return formatted_users