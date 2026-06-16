import logging

import requests
from core.utils.okta_helpers import get_okta_headers
from core.utils.rate_limit import handle_rate_limit
from django.conf import settings

from entities.okta_entities.auth_server.auth_server_models import AuthTrustedServer
from entities.okta_entities.auth_server.auth_server_serializers import (
    AuthTrustedServerSerializer,
)
from entities.okta_entities.auth_server.views.auth_server_base_viewset import (
    BaseAuthServerViewSet,
)

logger = logging.getLogger(__name__)

class AuthTrustedServerViewSet(BaseAuthServerViewSet):
    model = AuthTrustedServer
    serializer_class = AuthTrustedServerSerializer
    okta_endpoint = "api/v1/authorizationServers/{auth_server_id}/associatedServers"
    entity_type = "auth_trusted_servers"

    def fetch_from_okta(self, auth_server_id, request=None):
        if not auth_server_id:
            logger.error("Auth Server ID is required to fetch trusted servers.")
            return []

        url = f"{self.okta_base_url}/{self.okta_endpoint.format(auth_server_id=auth_server_id)}"
        params = {
            "trusted": "true"
        }
        headers = get_okta_headers(request)
        headers["Accept"] = "application/json"
        logger.info(f"Fetching trusted servers from Okta API: {url}")

        while True:
            response = requests.get(url, headers=headers, params=params)

            if handle_rate_limit(response):
                continue

            content = response.text.strip()
            if response.status_code == 200:
                if content:
                    try:
                        return response.json()
                    except Exception as e:
                        logger.error(f"Failed to decode JSON response: {e}")
                        return []
                else:
                    logger.warning(f"Empty response received for trusted servers of {auth_server_id}")
                    return []
            logger.error(f"Failed to fetch trusted servers. Status: {response.status_code}, Response: {content}")
            return []

    def extract_data(self, okta_data, auth_server_id=None):
        extracted_data = []
        trusted_ids = []
        for scope in okta_data:
            trusted_ids.append(scope.get("id"))
        extracted_data.append(
            {
                "auth_server_id": auth_server_id,
                "trusted": trusted_ids
            }
        )
        logger.info(f"Extracted {len(extracted_data)} trusted server records for auth server {auth_server_id}.")
        return extracted_data
