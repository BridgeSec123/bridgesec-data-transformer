import logging

import requests
from django.conf import settings
from core.utils.okta_helpers import get_okta_headers

from entities.okta_entities.apps.apps_models import AppToken
from entities.okta_entities.apps.apps_serializers import AppTokenSerializer
from entities.okta_entities.apps.views.apps_base_viewset import BaseAppViewSet

logger = logging.getLogger(__name__)


class AppTokenViewSet(BaseAppViewSet):
    okta_endpoint = "/api/v1/apps/{app_id}/tokens"
    entity_type = "okta_app_token"
    serializer_class = AppTokenSerializer
    model = AppToken

    def fetch_from_okta(self, app_id, request=None):
        if not app_id:
            logger.error("app_id is required to fetch app tokens")
            return [], 400, {}

        url = f"{settings.OKTA_API_URL}{self.okta_endpoint.format(app_id=app_id)}"
        headers = get_okta_headers(request)
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return response.json() if response.text.strip() else [], 200, {}
        logger.error(
            "Failed to fetch tokens for app %s: %s %s",
            app_id, response.status_code, response.text,
        )
        return [], response.status_code, {}

    def extract_data(self, okta_data, parent_record=None):
        items = okta_data if isinstance(okta_data, list) else []
        client_id = parent_record.get("client_id", "") if isinstance(parent_record, dict) else ""
        formatted_data = []
        for item in items:
            if not isinstance(item, dict):
                logger.warning("Skipping invalid record (not a dict): %s", item)
                continue
            formatted_data.append({
                "token_id": item.get("id", ""),
                "client_id": client_id,
                "user_id": item.get("userId", ""),
                "status": item.get("status", ""),
                "created": item.get("created", ""),
                "expires_at": item.get("expiresAt", ""),
                "scopes": item.get("scopes", []),
                "issuer": item.get("issuer", ""),
            })
        logger.info("Extracted %d App Token records for client %s", len(formatted_data), client_id)
        return formatted_data
