import logging

from rest_framework import status
from rest_framework.response import Response

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
            formatted_record = {
                "name": item.get("name"),
                "origin": item.get("origin"),
                "scopes": item.get("scopes"),
                "active": item.get("status"),
            }
            formatted_data.append(formatted_record)

        logger.info("Extracted %d trusted origins records", len(formatted_data))
        return formatted_data
    
    def fetch_and_store_data(self, db_name):
        try:
        # Step 1: Fetch data from Okta
            okta_response, status_code, headers = self.fetch_from_okta()
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
