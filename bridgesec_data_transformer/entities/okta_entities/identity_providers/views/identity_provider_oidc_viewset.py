import logging

from rest_framework import status
from rest_framework.response import Response

from entities.okta_entities.identity_providers.identity_provider_models import (
    IdentityProviderOIDC,
)
from entities.okta_entities.identity_providers.identity_provider_serializers import (
    IdentityProviderOIDCSerializer,
)
from entities.okta_entities.identity_providers.views.identity_provider_base_viewset import (
    BaseIdentityProviderViewSet,
)

logger = logging.getLogger(__name__)

class IdentityProviderOIDCViewSet(BaseIdentityProviderViewSet):
    entity_type = "okta_idp_oidc"
    serializer_class = IdentityProviderOIDCSerializer
    model = IdentityProviderOIDC
    
    def list(self, request, *args, **kwargs):
        """Retrieve all records from MongoDB and return serialized data."""
        start_date, end_date = super().list(request, *args, **kwargs)

        if not start_date or not end_date:
            identity_providers = self.model.objects()  # Fetch all documents using MongoEngine
            logger.info("Retrieved %d Identity Providers records from MongoDB", len(identity_providers))
            
        else:
            identity_providers = self.filter_by_date(start_date, end_date)
            logger.info(f"Retrieved {len(identity_providers)} Identity Providers between {start_date} and {end_date}")

        identity_providers_data = []
        for identity_provider in identity_providers:
            serializer = self.serializer_class(identity_provider)
            identity_providers_data.append(serializer.data)

        logger.info(f"Returning {len(identity_providers_data)} Identity Providers.")
        return Response(identity_providers_data, status=status.HTTP_200_OK)

    def extract_data(self, okta_data):
        logger.info("Extracting data from Okta response")
        extracted_data = super().extract_data(okta_data)

        formatted_data = []
        
        for record in extracted_data:
            if record.get("type") == "OIDC":
                protocol = record.get("protocol", {})
                policy = record.get("policy", {})
                endpoints = protocol.get("endpoints", {})
                client_credentials = protocol.get("credentials", {}).get("client", {})
                formatted_record = {
                    "name": record.get("name", ""),
                    "authorization_url": endpoints.get("authorization", {}).get("url", ""),
                    "authorization_binding": endpoints.get("authorization", {}).get("binding", ""),
                    "token_url": endpoints.get("token", {}).get("url", ""),
                    "token_binding": endpoints.get("token", {}).get("binding", ""),
                    "user_info_url": endpoints.get("user_info", {}).get("url", ""),
                    "user_info_binding": endpoints.get("user_info", {}).get("binding", ""),
                    "jwks_url": endpoints.get("jwks", {}).get("url", ""),
                    "jwks_binding": endpoints.get("jwks", {}).get("binding", ""),
                    "scopes": protocol.get("scopes", []),
                    "client_id": client_credentials.get("client_id", ""),
                    "client_secret": client_credentials.get("client_secret", ""),
                    "issuer_url": protocol.get("issuer", {}).get("url", ""),
                    "username_template": policy.get("subject", {}).get("userNameTemplate", {}).get("template"),
                }
                formatted_data.append(formatted_record)
        logger.info("Extracted and formatted %d Identity Provider records from Okta", len(formatted_data))
        
        return formatted_data