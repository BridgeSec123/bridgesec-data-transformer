import logging

import requests
from django.conf import settings

from entities.okta_entities.auth_server.auth_server_models import (
    AuthorizationServerScope,
)
from entities.okta_entities.auth_server.auth_server_serializers import (
    AuthorizationServerScopeSerializer,
)
from entities.okta_entities.auth_server.views.auth_server_base_viewset import (
    BaseAuthServerViewSet,
)

logger = logging.getLogger(__name__)

class AuthorizationServerScopeViewSet(BaseAuthServerViewSet):
    model = AuthorizationServerScope
    serializer_class = AuthorizationServerScopeSerializer
    okta_endpoint = "api/v1/authorizationServers/{auth_server_id}/scopes"
    entity_type = "auth_server_scopes"

    def fetch_from_okta(self, auth_server_id):
        if not auth_server_id:
            logger.error("Auth Server ID is required to fetch scopes.")
            return []

        url = f"{settings.OKTA_API_URL}/{self.okta_endpoint.format(auth_server_id=auth_server_id)}"
        headers = {"Authorization": f"SSWS {settings.OKTA_API_TOKEN}"}

        logger.info(f"Fetching scopes from Okta API: {url}")
        response = requests.get(url, headers=headers)

        content = response.text.strip()
        if response.status_code == 200:
            if content:
                try:
                    return response.json()
                except Exception as e:
                    logger.error(f"Failed to decode JSON response: {e}")
                    return []
            else:
                logger.warning(f"Empty response received for scopes of {auth_server_id}")
                return []
        else:
            logger.error(f"Failed to fetch scopes. Status: {response.status_code}, Response: {content}")
            return []

    def extract_data(self, okta_data, auth_server_id):
        extracted_data = []
        for scope in okta_data:
            record = {
                "auth_server_id": auth_server_id,
                "name": scope.get("name"),
                "display_name": scope.get("displayName"),
                "description": scope.get("description"),
                "consent": scope.get("consent"),
                "metadata_publish": scope.get("metadataPublish"),
                "default": scope.get("default", False),
                "optional": scope.get("optional", False),
            }
            extracted_data.append(record)

        logger.info(f"Extracted {len(extracted_data)} scope records for auth server {auth_server_id}.")
        return extracted_data
