import logging

from entities.views.base_view import BaseEntityViewSet
from entities.okta_entities.requests.request_condition_models import RequestSettings
from entities.okta_entities.requests.request_condition_serializers import RequestSettingsSerializer

logger = logging.getLogger(__name__)


class RequestSettingsViewSet(BaseEntityViewSet):
    okta_endpoint = "/governance/api/v2/resources"
    entity_type = "request_settings"
    serializer_class = RequestSettingsSerializer
    model = RequestSettings

    def extract_data(self, okta_data):
        """Extract and format request settings data from Okta response"""
        formatted_data = []

        # Check if okta_data is a list or single object
        items = okta_data if isinstance(okta_data, list) else [okta_data]

        for item in items:
            formatted_data.append({
                "resource_id": item.get("resourceId", "")
            })

        logger.info("Extracted %d Request Settings records", len(formatted_data))
        return formatted_data
