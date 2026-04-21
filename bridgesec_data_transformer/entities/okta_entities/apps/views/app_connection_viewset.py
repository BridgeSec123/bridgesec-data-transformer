import logging

import requests
from django.conf import settings
from core.utils.okta_helpers import get_okta_headers

from entities.okta_entities.apps.apps_models import AppConnection
from entities.okta_entities.apps.apps_serializers import AppConnectionSerializer
from entities.okta_entities.apps.views.apps_base_viewset import BaseAppViewSet

logger = logging.getLogger(__name__)

SENSITIVE_PROFILE_FIELDS = {"token", "adminPassword"}


class AppConnectionViewSet(BaseAppViewSet):
    okta_endpoint = "/api/v1/apps/{app_id}/connections/default"
    entity_type = "okta_app_connection"
    serializer_class = AppConnectionSerializer
    model = AppConnection

    def fetch_from_okta(self, app_id, request=None):
        if not app_id:
            logger.error("app_id is required to fetch app connection")
            return {}, 400, {}

        url = f"{settings.OKTA_API_URL}{self.okta_endpoint.format(app_id=app_id)}"
        headers = get_okta_headers(request)
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return response.json() if response.text.strip() else {}, 200, {}
        if response.status_code in (404, 400):
            return {}, response.status_code, {}
        logger.warning(
            "Failed to fetch connection for app %s: %s %s",
            app_id, response.status_code, response.text,
        )
        return {}, response.status_code, {}

    def extract_data(self, okta_data, app_info=None):
        if not isinstance(okta_data, dict) or not okta_data:
            return []

        app_id = app_info.get("app_id", "") if isinstance(app_info, dict) else ""

        raw_profile = okta_data.get("profile", {}) or {}
        profile = {k: v for k, v in raw_profile.items() if k not in SENSITIVE_PROFILE_FIELDS}

        record = {
            "app_id": app_id,
            "status": okta_data.get("status", ""),
            "auth_scheme": okta_data.get("authScheme", ""),
            "base_url": okta_data.get("baseUrl", ""),
            "profile": profile,
        }
        logger.info("Extracted App Connection record for app %s", app_id)
        return [record]
