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

    def list(self, request, *args, **kwargs):
        start_date, end_date = super().list(request, *args, **kwargs)

        if not start_date or not end_date:
            behaviors = self.model.objects()
            logger.info("Retrieved %d behavior records", len(behaviors))
        else:
            behaviors = self.filter_by_date(start_date, end_date)
            logger.info("Retrieved %d behavior records between %s and %s", len(behaviors), start_date, end_date)

        serializer = self.serializer_class(behaviors, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def extract_data(self, okta_data):
        extracted_data = super().extract_data(okta_data)
        formatted_data = []

        for item in extracted_data:
            formatted_record = {
                "name": item.get("name"),
                "type": item.get("type"),
                "status": item.get("status"),
                "velocity": item.get("velocity"),
                "location_granularity_type": item.get("type"),
                "number_of_authentications": item.get("type")
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
