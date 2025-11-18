import logging

import requests
from core.utils.rate_limit import handle_rate_limit, rate_limit_headers
from django.conf import settings

from entities.okta_entities.apps.apps_models import  AppUserSchemaProperty
from entities.okta_entities.apps.apps_serializers import  AppUserSchemaPropertySerializer
from entities.okta_entities.apps.views.apps_base_viewset import BaseAppViewSet

logger = logging.getLogger(__name__)

class AppUserSchemaPropertyViewSet(BaseAppViewSet):
    okta_endpoint = "/api/v1/meta/schemas/apps/{appId}/default"
    entity_type = "okta_app_user_schema_property"
    serializer_class = AppUserSchemaPropertySerializer
    model = AppUserSchemaProperty

    def fetch_from_okta(self, app_id):
        """
        Fetch user schema for a specific app from Okta.
        """
        base_url = settings.OKTA_API_URL
        headers = {"Authorization": f"SSWS {settings.OKTA_API_TOKEN}"}

        # API call to get user schema for this app
        schema_url = f"{base_url}/api/v1/meta/schemas/apps/{app_id}/default"
        logger.info(f"Fetching user schema for app_id: {app_id}")

        response = requests.get(schema_url, headers=headers)

        if handle_rate_limit(response):
            logger.warning(f"Rate limit hit for app_id: {app_id}")
            return {"error": "Rate limit hit."}, 429, rate_limit_headers(response)

        if response.status_code != 200:
            logger.error(f"Failed to fetch user schema for app {app_id}: {response.text}")
            return {"error": f"Failed to fetch user schema: {response.text}"}, response.status_code, rate_limit_headers(response)

        schema_data = response.json()
        logger.info(f"Fetched user schema for app_id: {app_id}")

        return schema_data, 200, rate_limit_headers(response)

    def extract_data(self, okta_data, app=None):
        """
        Formats user schema property data.
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
            "array_enum": user.get("array_enum", []),
            "array_one_of": user.get("array_one_of", []),
            "array_type": user.get("array_type", ""),
            "enum": user.get("enum", []),
            "description": user.get("description", ""),
            "external_name": user.get("external_name", ""),
            "external_namespace": user.get("external_namespace", ""),
            "master": base.get("properties", {}).get("userName", {}).get("master", {}).get("type", ""),
            "max_length": user.get("max_length", 0),
            "min_length": user.get("min_length", 0),
            "one_of": user.get("one_of", []),
            "permissions": user.get("permissions", ""),
            "required": is_required,
            "scope": user.get("scope", ""),
            "unique": user.get("unique", ""),
            "union": user.get("union", ""),
            "user_type": user.get("userType", "default")
        }

        logger.info(f"Formatted user schema property for app: {app_id}")
        return [formatted_record]
