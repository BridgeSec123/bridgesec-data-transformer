import logging

import requests
from core.utils.okta_helpers import get_okta_headers
from core.utils.rate_limit import handle_rate_limit, rate_limit_headers
from django.conf import settings

from entities.okta_entities.apps.apps_models import AppUserBaseSchemaProperty
from entities.okta_entities.apps.apps_serializers import AppUserBaseSchemaPropertySerializer
from entities.okta_entities.apps.views.apps_base_viewset import BaseAppViewSet

logger = logging.getLogger(__name__)

class AppUserBaseSchemaPropertyViewSet(BaseAppViewSet):
    okta_endpoint = "/api/v1/meta/schemas/apps/{appId}/default"
    entity_type = "okta_app_user_base_schema_property"
    serializer_class = AppUserBaseSchemaPropertySerializer
    model = AppUserBaseSchemaProperty

    def fetch_from_okta(self, app_id, request=None):
        """
        Fetch user base schema for a specific app from Okta.
        """
        base_url = settings.OKTA_API_URL
        headers = get_okta_headers(request)

        # API call to get user base schema for this app
        schema_url = f"{base_url}/api/v1/meta/schemas/apps/{app_id}/default"
        logger.info(f"Fetching user base schema for app_id: {app_id}")

        response = requests.get(schema_url, headers=headers)

        if handle_rate_limit(response):
            logger.warning(f"Rate limit hit for app_id: {app_id}")
            return {"error": "Rate limit hit."}, 429, rate_limit_headers(response)

        if response.status_code != 200:
            logger.error(f"Failed to fetch user base schema for app {app_id}: {response.text}")
            return {"error": f"Failed to fetch user base schema: {response.text}"}, response.status_code, rate_limit_headers(response)

        schema_data = response.json()
        logger.info(f"Fetched user base schema for app_id: {app_id}")

        return schema_data, 200, rate_limit_headers(response)

    def extract_data(self, okta_data, app=None):
        """
        Formats user base schema property data.
        """
        if not app:
            logger.warning("No app info provided for formatting")
            return []

        app_id = app.get("app_id")

        user = okta_data
        base = user.get("definitions", {}).get("base", {})

        # Get required field safely
        required_fields = base.get("required", [])
        is_required = bool(required_fields[0]) if required_fields else False

        formatted_record = {
            "app_id": app_id,
            "index": user.get("name", ""),
            "title": user.get("title", ""),
            "type": user.get("type", ""),
            "master": base.get("properties", {}).get("userName", {}).get("master", {}).get("type", ""),
            "pattern": user.get("pattern", ""),
            "permissions": user.get("permissions", ""),
            "required": is_required,
            "user_type": user.get("userType", "default")
        }

        logger.info(f"Formatted user base schema property for app: {app_id}")
        return [formatted_record]
