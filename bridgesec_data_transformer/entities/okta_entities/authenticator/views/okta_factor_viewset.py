import logging

from entities.okta_entities.authenticator.views.authenticator_base_viewset import BaseAuthenticatorViewSet
from entities.okta_entities.authenticator.authenticator_models import OktaFactor
from entities.okta_entities.authenticator.authenticator_serializers import (
    OktaFactorSerializer,
)

logger = logging.getLogger(__name__)

class OktaFactorViewSet(BaseAuthenticatorViewSet):
    okta_endpoint = "/api/v1/org/factors"
    entity_type = "okta_factors"
    serializer_class = OktaFactorSerializer
    model = OktaFactor

    def extract_data(self, okta_data):
        extracted_data = super().extract_data(okta_data)
        formatted_data = []
        for data in extracted_data:
            formatted_record = {
                "provider_id": data.get("id"),
                "active": True if data.get("status") == "ACTIVE" else False,
            }
            formatted_data.append(formatted_record)
        
        logger.info(f"Extracted {len(formatted_data)} authenticators from Okta response")
        return formatted_data
    
