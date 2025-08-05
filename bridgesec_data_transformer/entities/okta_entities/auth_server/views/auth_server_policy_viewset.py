import logging

import requests
from django.conf import settings

from entities.okta_entities.auth_server.auth_server_models import (
    AuthorizationServerPolicy,
)
from entities.okta_entities.auth_server.auth_server_serializers import (
    AuthorizationServerPolicySerializer,
)
from entities.okta_entities.auth_server.views.auth_server_base_viewset import (
    BaseAuthServerViewSet,
)

logger = logging.getLogger(__name__)

class AuthorizationServerPolicyViewSet(BaseAuthServerViewSet):
    queryset = AuthorizationServerPolicy.objects.all()
    okta_endpoint = "/api/v1/authorizationServers/{auth_server_id}/policies"
    entity_type = "auth_server_policy"
    serializer_class = AuthorizationServerPolicySerializer
    model = AuthorizationServerPolicy

    def fetch_from_okta(self, auth_server_id):
        """
        Fetch policies for a specific Authorization Server ID.
        """
        if not auth_server_id:
            logger.error("Auth Server ID is required to fetch policies.")
            return []

        url = f"{settings.OKTA_API_URL}/{self.okta_endpoint.format(auth_server_id=auth_server_id)}"
        headers = {"Authorization": f"SSWS {settings.OKTA_API_TOKEN}"}

        logger.info(f"Fetching data from Okta API: {url}")
        
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            logger.info(f"Successfully fetched policies for Authorization Server ID: {auth_server_id}.")
            return response.json()
        else:
            logger.error(f"Failed to fetch policies for Authorization Server ID: {auth_server_id}. Status Code: {response.status_code}, Response: {response.text}")
            return []

    def extract_data(self, okta_data, auth_server_id=None):
        extracted = []
        for item in okta_data:
            record = {
                "auth_server_id": auth_server_id,
                "policy_id": item.get("id"),
                "name": item.get("name", ""),
                "client_whitelist": item.get("conditions", {}).get("clients", {}).get("include", []),
                "description": item.get("description", ""),
                "priority": item.get("priority", ""),
                "status": item.get("status", ""),
            }
            extracted.append(record)

        logger.info(f"Extracted {len(extracted)} policies for Authorization Server {auth_server_id}")
        return extracted
