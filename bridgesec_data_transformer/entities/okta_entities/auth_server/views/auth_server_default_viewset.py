import logging

from entities.okta_entities.auth_server.auth_server_models import (
    AuthorizationServerDefault,
)
from entities.okta_entities.auth_server.auth_server_serializers import (
    AuthorizationServerDefaultSerializer,
)
from entities.okta_entities.auth_server.views.auth_server_base_viewset import (
    BaseAuthServerViewSet,
)

logger = logging.getLogger(__name__)

class AuthorizationServerDefaultViewSet(BaseAuthServerViewSet):
    okta_endpoint = "/api/v1/authorizationServers/default"
    entity_type = "auth_servers_default"
    serializer_class = AuthorizationServerDefaultSerializer
    model = AuthorizationServerDefault
    
    def extract_data(self, okta_data):
        return [
            {
                "audiences": okta_data.get("audiences"),
                "credentials_rotation_mode": okta_data.get("credentials").get("signing").get("rotationMode"),
                "description": okta_data.get("description"),
                "issuer_mode": okta_data.get("issuerMode"),
                "name": okta_data.get("name"),
                "status": okta_data.get("status"),
            }
        ]
