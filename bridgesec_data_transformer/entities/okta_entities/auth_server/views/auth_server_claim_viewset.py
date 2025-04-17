import logging

import requests
from django.conf import settings

from entities.okta_entities.auth_server.auth_server_models import (
    AuthorizationServerClaim,
)
from entities.okta_entities.auth_server.auth_server_serializers import (
    AuthorizationServerClaimSerializer,
)
from entities.okta_entities.auth_server.views.auth_server_base_viewset import (
    BaseAuthServerViewSet,
)

logger = logging.getLogger(__name__)

class AuthorizationServerClaimViewSet(BaseAuthServerViewSet):
    queryset = AuthorizationServerClaim.objects.all()
    okta_endpoint = "/api/v1/authorizationServers/{auth_server_id}/claims"
    entity_type = "auth_server_claims"
    serializer_class = AuthorizationServerClaimSerializer
    model = AuthorizationServerClaim

    def fetch_from_okta(self, auth_server_id):
        """
        Fetch claims for a specific Authorization Server ID.
        """
        if not auth_server_id:
            logger.error("Auth Server ID is required to fetch Claims")
            return []

        url = f"{settings.OKTA_API_URL}/{self.okta_endpoint.format(auth_server_id=auth_server_id)}"
        headers = {"Authorization": f"SSWS {settings.OKTA_API_TOKEN}"}

        logger.info(f"Fetching data from Okta API: {url}")
        
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            logger.info(f"Successfully fetched Claims for Authorization Server ID: {auth_server_id}.")
            return response.json()
        else:
            logger.error(f"Failed to fetch Claims for Authorization Server ID: {auth_server_id}. Status Code: {response.status_code}, Response: {response.text}")
            return []

    def extract_data(self, okta_data, auth_server_id=None):
        extracted = []
        for item in okta_data:
            record = {
                "auth_server_id": auth_server_id,
                "claim_type": item.get("claimType"),
                "name": item.get("name"),
                "value": item.get("value", ""),
                "alway_include_in_token": item.get("alwaysIncludeInToken"),
                "group_filter_type": item.get("groupFilterType", ""),
                "scopes": item.get("conditions", {}).get("scopes", []),
                "status": item.get("status"),
                "value_type": item.get("valueType"),
            }
            extracted.append(record)

        logger.info(f"Extracted {len(extracted)} claims for Authorization Server {auth_server_id}")
        return extracted
