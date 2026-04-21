import logging

import requests
from django.conf import settings
from core.utils.okta_helpers import get_okta_headers

from entities.okta_entities.auth_server.auth_server_models import AuthorizationServerClient
from entities.okta_entities.auth_server.auth_server_serializers import AuthorizationServerClientSerializer
from entities.okta_entities.auth_server.views.auth_server_base_viewset import BaseAuthServerViewSet

logger = logging.getLogger(__name__)


class AuthorizationServerClientsViewSet(BaseAuthServerViewSet):
    okta_endpoint = "api/v1/authorizationServers/{auth_server_id}/clients"
    entity_type = "auth_server_clients"
    serializer_class = AuthorizationServerClientSerializer
    model = AuthorizationServerClient

    def fetch_clients(self, auth_server_id, request=None):
        url = f"{settings.OKTA_API_URL}/api/v1/authorizationServers/{auth_server_id}/clients"
        headers = get_okta_headers(request)
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json() if response.text.strip() else []
        logger.error("Failed to fetch clients for auth_server %s: %s", auth_server_id, response.text)
        return []

    def fetch_tokens(self, auth_server_id, client_id, request=None):
        url = f"{settings.OKTA_API_URL}/api/v1/authorizationServers/{auth_server_id}/clients/{client_id}/tokens"
        headers = get_okta_headers(request)
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json() if response.text.strip() else []
        logger.error(
            "Failed to fetch tokens for auth_server %s client %s: %s",
            auth_server_id, client_id, response.text,
        )
        return []

    def extract_data(self, okta_data, auth_server_id=None, client_id=None):
        items = okta_data if isinstance(okta_data, list) else []
        formatted_data = []
        for item in items:
            if not isinstance(item, dict):
                logger.warning("Skipping invalid record (not a dict): %s", item)
                continue
            formatted_data.append({
                "token_id": item.get("id", ""),
                "auth_server_id": auth_server_id or "",
                "client_id": client_id or "",
                "created": item.get("created", ""),
                "expires_at": item.get("expiresAt", ""),
                "issuer": item.get("issuer", ""),
                "last_updated": item.get("lastUpdated", ""),
                "scopes": item.get("scopes", []),
                "status": item.get("status", ""),
                "user_id": item.get("userId", ""),
            })
        return formatted_data
