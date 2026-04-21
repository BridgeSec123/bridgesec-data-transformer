import logging

import requests
from django.conf import settings
from core.utils.okta_helpers import get_okta_headers

from entities.okta_entities.auth_server.auth_server_models import AuthorizationServerKey
from entities.okta_entities.auth_server.auth_server_serializers import AuthorizationServerKeySerializer
from entities.okta_entities.auth_server.views.auth_server_base_viewset import BaseAuthServerViewSet

logger = logging.getLogger(__name__)


class AuthorizationServerKeysViewSet(BaseAuthServerViewSet):
    okta_endpoint = "/api/v1/authorizationServers/{auth_server_id}/credentials/keys"
    entity_type = "auth_server_keys"
    serializer_class = AuthorizationServerKeySerializer
    model = AuthorizationServerKey

    def fetch_from_okta(self, auth_server_id, request=None):
        if not auth_server_id:
            logger.error("Auth Server ID is required to fetch keys")
            return []

        url = f"{settings.OKTA_API_URL}{self.okta_endpoint.format(auth_server_id=auth_server_id)}"
        headers = get_okta_headers(request)
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return response.json() if response.text.strip() else []
        logger.error(
            "Failed to fetch keys for auth server %s: %s %s",
            auth_server_id, response.status_code, response.text,
        )
        return []

    def extract_data(self, okta_data, auth_server_id=None):
        items = okta_data if isinstance(okta_data, list) else []
        formatted_data = []
        for item in items:
            if not isinstance(item, dict):
                logger.warning("Skipping invalid record (not a dict): %s", item)
                continue
            kid = item.get("kid", "")
            formatted_data.append({
                "key_id": kid,
                "auth_server_id": auth_server_id or "",
                "alg": item.get("alg", ""),
                "e": item.get("e", ""),
                "kid": kid,
                "n": item.get("n", ""),
                "status": item.get("status", ""),
                "use": item.get("use", ""),
            })
        logger.info("Extracted %d Auth Server Key records for %s", len(formatted_data), auth_server_id)
        return formatted_data
