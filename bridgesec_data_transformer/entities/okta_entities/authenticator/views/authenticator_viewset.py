import logging

from entities.okta_entities.authenticator.authenticator_models import Authenticator
from entities.okta_entities.authenticator.authenticator_serializers import (
    AuthenticatorSerializer,
)
from entities.views.base_view import BaseEntityViewSet

logger = logging.getLogger(__name__)

class AuthenticatorViewSet(BaseEntityViewSet):
    okta_endpoint = "/api/v1/authenticators"
    entity_type = "authenticators"
    serializer_class = AuthenticatorSerializer
    model = Authenticator

    def extract_data(self, okta_data):
        extracted_data = super().extract_data(okta_data)
        formatted_data = []
        for data in extracted_data:
            formatted_record = {
                "name": data.get("name"),
                "key": data.get("key"),
                "status": data.get("status"),
                "legacy_ignore_name": data.get("legacy_ignore_name"),
                "provider_auth_port": data.get("provider_auth_port"),
                "provider_host": data.get("provider_host"),
                "provider_hostname": data.get("provider_hostname"),
                "provider_integration_key": data.get("provider_integration_key"),
                "provider_json": data.get("provider_json"),
                "provider_secret_key": data.get("provider_secret_key"),
                "provider_shared_secret": data.get("provider_shared_secret"),
                "provider_user_name_template": data.get("provider_user_name_template"),
                "settings": data.get("settings", {}),
            }
            formatted_data.append(formatted_record)
        
        logger.info(f"Extracted {len(formatted_data)} authenticators from Okta response")
        return formatted_data
    
    def fetch_and_store_data(self, db_name):
        """Fetch data from Okta and store in MongoDB."""
        try:
            # Step 1: Fetch data from Okta
            okta_response, status_code, headers = self.fetch_from_okta()
            logger.info("Fetched authenticators data from Okta")

            # Step 2: Extract and format data
            extracted_data = self.extract_data(okta_response)
            logger.info("Extracted %d authenticators records from Okta response", len(extracted_data))

            # Step 3: Store extracted data in MongoDB
            self.store_data(extracted_data, db_name=db_name)
            logger.info("Stored %d authenticators records in MongoDB database: %s", len(extracted_data), db_name)

            return {"authenticators": extracted_data}

        except Exception as e:
            logger.error("Error in fetch_and_store_data: %s", str(e), exc_info=True)
            return {
                "error": str(e),
                "message": "Failed to fetch and store authenticators data."
            }
