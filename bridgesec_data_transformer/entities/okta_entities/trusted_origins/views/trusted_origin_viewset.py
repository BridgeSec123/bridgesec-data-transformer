import logging

from entities.okta_entities.trusted_origins.trusted_origin_models import TrustedOrigin
from entities.okta_entities.trusted_origins.trusted_origin_serializers import (
    TrustedOriginSerializer,
)
from entities.views.base_view import BaseEntityViewSet

logger = logging.getLogger(__name__)

class TrustedOriginViewSet(BaseEntityViewSet):
    okta_endpoint = "/api/v1/trustedOrigins"
    entity_type = "trusted_origins"
    serializer_class = TrustedOriginSerializer
    model = TrustedOrigin

    def extract_data(self, okta_data):
        extracted_data = super().extract_data(okta_data)
        formatted_data = []

        for item in extracted_data:
            if not isinstance(item, dict):
                logger.warning(f"Skipping invalid record (not a dict): {item}")
                continue
            # Get the first scope type if multiple exist, or default to empty string
            scopes = item.get("scopes", [])
            scope_value = []
            if scopes and len(scopes) > 0:
                # Take the first scope's type and convert to uppercase
                scopes = scopes[0].get("type", "").upper()
                scope_value.append(scopes)

            formatted_record = {
                "trusted_id" : item.get("id"),
                "name": item.get("name"),
                "origin": item.get("origin"),
                "scopes": scope_value,  # Now storing as a single string, not a list
                "active": item.get("status"),
            }
            formatted_data.append(formatted_record)

        logger.info("Extracted %d trusted origins records", len(formatted_data))
        return formatted_data
    
    def fetch_and_store_data(self, db_name, request=None):
        try:
        # Step 1: Fetch data from Okta
            okta_response, status_code, headers = self.fetch_from_okta(request=request)
            logger.info("Fetched trusted origins data from Okta")

            # Step 2: Extract and format data
            extracted_data = self.extract_data(okta_response)
            logger.info("Extracted %d trusted origins records from Okta response", len(extracted_data))

            # Step 3: Store extracted data in MongoDB
            self.store_data(extracted_data, db_name=db_name)
            logger.info("Stored %d trusted origins records in MongoDB database: %s", len(extracted_data), db_name)

            return {"trusted_origins": extracted_data}

        except Exception as e:
            logger.error("Error in fetch_and_store_data: %s", str(e), exc_info=True)
            return {
                "error": str(e),
                "message": "Failed to fetch and store trusted origins data."
            }
