import logging

from entities.views.base_view import BaseEntityViewSet
from entities.okta_entities.requests.request_condition_models import RequestSequence
from entities.okta_entities.requests.request_condition_serializers import RequestSequenceSerializer

logger = logging.getLogger(__name__)


class RequestSequenceViewSet(BaseEntityViewSet):
    okta_endpoint = "/governance/api/v2/resources"
    entity_type = "request_sequences"
    serializer_class = RequestSequenceSerializer
    model = RequestSequence

    def extract_data(self, okta_data):
        """Extract and format request sequence data from Okta response"""
        formatted_data = []

        # Check if okta_data is a list or single object
        items = okta_data if isinstance(okta_data, list) else [okta_data]

        for item in items:
            formatted_data.append({
                "resource_id": item.get("resourceId", ""),
                "sequence_id": item.get("id", "")
            })

        logger.info("Extracted %d Request Sequence records", len(formatted_data))
        return formatted_data
