import logging

from rest_framework import status
from rest_framework.response import Response

from entities.okta_entities.behavior.behavior_models import Behavior
from entities.okta_entities.behavior.behavior_serializer import BehaviorSerializer
from entities.views.base_view import BaseEntityViewSet

logger = logging.getLogger(__name__)

class BehaviorViewSet(BaseEntityViewSet):
    okta_endpoint = "/api/v1/behaviors"
    entity_type = "behavior"
    serializer_class = BehaviorSerializer
    model = Behavior

    def extract_data(self, okta_data):
        extracted_data = super().extract_data(okta_data)
        formatted_data = []

        for record in extracted_data:
            settings= record.get("settings",{})
            formatted_record = {
                "name": record.get("name", ""),
                "type": record.get("type", ""),
                "status": record.get("status", ""),
                "velocity": settings.get("velocityKph", 0),
                "location_granularity_type": settings.get("granularity", ""),
                "number_of_authentications": record.get("number_of_authentications", 0),
                "radius_from_location": settings.get("radiusKilometers", 0),
                }
            
            formatted_data.append(formatted_record)

        logger.info("Extracted %d behavior records", len(formatted_data))
        return formatted_data
    
    def fetch_and_store_data(self, db_name):
        try:
        # Step 1: Fetch data from Okta
            okta_response, status_code, headers = self.fetch_from_okta()
            logger.info("Fetched behavior data from Okta")

            # Step 2: Extract and format data
            extracted_data = self.extract_data(okta_response)
            logger.info("Extracted %d behavior records from Okta response", len(extracted_data))

            # Step 3: Store extracted data in MongoDB
            self.store_data(extracted_data, db_name=db_name)
            logger.info("Stored %d behavior records in MongoDB database: %s", len(extracted_data), db_name)

            return {"behavior":extracted_data}

        except Exception as e:
            logger.error("Error in fetch_and_store_data: %s", str(e), exc_info=True)
            return {
                "error": str(e),
                "message": "Failed to fetch and store behavior data."
            }
