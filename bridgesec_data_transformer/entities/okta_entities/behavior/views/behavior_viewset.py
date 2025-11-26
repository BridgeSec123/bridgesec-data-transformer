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

    BEHAVIOR_TYPES = ['ANOMALOUS_LOCATION', 'ANOMALOUS_DEVICE', 'ANOMALOUS_IP', 'VELOCITY']
    LOCATION_GRANULARITY_TYPES = ['LAT_LONG', 'CITY', 'COUNTRY', 'SUBDIVISION']
    STATUS_CHOICES = ['ACTIVE', 'INACTIVE']

    def validate_behavior_data(self, data):
        """Validate behavior data based on type and requirements"""
        errors = []
        behavior_type = data.get('type')

        # Validate behavior type
        if behavior_type and behavior_type not in self.BEHAVIOR_TYPES:
            errors.append(f"Invalid behavior type: {behavior_type}. Must be one of {self.BEHAVIOR_TYPES}")

        # Validate status
        status_value = data.get('status')
        if status_value and status_value not in self.STATUS_CHOICES:
            errors.append(f"Invalid status: {status_value}. Must be one of {self.STATUS_CHOICES}")

        # Type-specific validations
        if behavior_type in ['ANOMALOUS_LOCATION', 'ANOMALOUS_DEVICE', 'ANOMALOUS_IP']:
            if not data.get('number_of_authentications'):
                errors.append(f"number_of_authentications is required for {behavior_type} behavior type")

        if behavior_type == 'ANOMALOUS_LOCATION':
            location_granularity = data.get('location_granularity_type')

            if not location_granularity:
                errors.append("location_granularity_type is required for ANOMALOUS_LOCATION behavior type")
            elif location_granularity not in self.LOCATION_GRANULARITY_TYPES:
                errors.append(f"Invalid location_granularity_type: {location_granularity}. Must be one of {self.LOCATION_GRANULARITY_TYPES}")

            if location_granularity == 'LAT_LONG':
                radius = data.get('radius_from_location')
                if not radius:
                    errors.append("radius_from_location is required when location_granularity_type is LAT_LONG")
                elif radius < 5:
                    errors.append("radius_from_location must be at least 5 kilometers")

        if behavior_type == 'VELOCITY':
            velocity = data.get('velocity')
            if not velocity:
                errors.append("velocity is required for VELOCITY behavior type")
            elif velocity < 1:
                errors.append("velocity must be at least 1 kilometer per hour")

        return errors

    def extract_data(self, okta_data):
        extracted_data = super().extract_data(okta_data)
        formatted_data = []

        for record in extracted_data:
            settings = record.get("settings", {})

            # Extract data with proper field mappings
            formatted_record = {
                "behavior_id": record.get("id", ""),
                "name": record.get("name", ""),
                "type": record.get("type", ""),
                "status": record.get("status", "ACTIVE"),  # Default to ACTIVE if not provided
                "velocity": settings.get("velocityKph"),
                "location_granularity_type": settings.get("granularity"),
                "number_of_authentications": settings.get("maxEventsUsedForEvaluation"),
                "radius_from_location": settings.get("radiusKilometers"),
            }

            # Remove None values for optional fields
            formatted_record = {k: v for k, v in formatted_record.items() if v is not None or k in ['behavior_id', 'name', 'type']}

            # Validate the formatted record
            validation_errors = self.validate_behavior_data(formatted_record)
            if validation_errors:
                logger.warning(f"Validation errors for behavior {formatted_record.get('behavior_id')}: {validation_errors}")

            formatted_data.append(formatted_record)

        logger.info("Extracted %d behavior records", len(formatted_data))
        return formatted_data
    
    def fetch_and_store_data(self, db_name, request=None):
        try:
        # Step 1: Fetch data from Okta
            okta_response, status_code, headers = self.fetch_from_okta(request=request)
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
