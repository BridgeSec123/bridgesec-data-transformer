import logging

from entities.okta_entities.auth_server.auth_server_models import AuthorizationServer
from entities.okta_entities.auth_server.auth_server_serializers import (
    AuthorizationServerSerializer,
)
from entities.okta_entities.auth_server.views.auth_server_base_viewset import (
    BaseAuthServerViewSet,
)

logger = logging.getLogger(__name__)

class AuthorizationServerViewSet(BaseAuthServerViewSet):
    queryset = AuthorizationServer.objects.all()
    okta_endpoint = "/api/v1/authorizationServers"
    entity_type = "auth_servers"
    serializer_class = AuthorizationServerSerializer
    model = AuthorizationServer

    def extract_data(self, okta_data):
        extracted_data = super().extract_data(okta_data)
        formatted_data = []
        for data in extracted_data:
            formatted_record = {
                "auth_server_id": data.get("id"),
                "name": data.get("name"),
                "audiences": data.get("audiences"),
                "description": data.get("description"),
                "issuer_mode": data.get("issuerMode"),
                "status": data.get("status")
            }
            formatted_data.append(formatted_record)
            
        logger.info(f"Formatted {len(formatted_data)} records for entity type {self.entity_type}")
        return formatted_data
