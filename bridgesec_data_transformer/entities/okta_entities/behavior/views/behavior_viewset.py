import logging

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

        if behavior_type and behavior_type not in self.BEHAVIOR_TYPES:
            errors.append(f"Invalid behavior type: {behavior_type}. Must be one of {self.BEHAVIOR_TYPES}")

        status_value = data.get('status')
        if status_value and status_value not in self.STATUS_CHOICES:
            errors.append(f"Invalid status: {status_value}. Must be one of {self.STATUS_CHOICES}")

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

            formatted_record = {
                "behavior_id": record.get("id", ""),
                "name": record.get("name", ""),
                "type": record.get("type", ""),
                "status": record.get("status", "ACTIVE"),
                "velocity": settings.get("velocityKph"),
                "location_granularity_type": settings.get("granularity"),
                "number_of_authentications": settings.get("maxEventsUsedForEvaluation"),
                "radius_from_location": settings.get("radiusKilometers"),
            }

            formatted_record = {k: v for k, v in formatted_record.items() if v is not None or k in ['behavior_id', 'name', 'type']}
            formatted_data.append(formatted_record)

        return formatted_data

    def fetch_and_store_data(self, db_name, request=None):
        try:
            okta_response, status_code, _ = self.fetch_from_okta(request=request)
            if status_code == 200:
                extracted_data = self.extract_data(okta_response)
                self.store_data(extracted_data, db_name=db_name)
                return {"behavior": extracted_data}
            else:
                return {"behavior": []}
        except Exception as e:
            logger.exception(f"Error in fetch_and_store_data: {str(e)}")
            return {"behavior": []}
