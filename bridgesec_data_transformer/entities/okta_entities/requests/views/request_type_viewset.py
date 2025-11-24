import logging

from entities.views.base_view import BaseEntityViewSet
from entities.okta_entities.requests.request_condition_models import RequestType
from entities.okta_entities.requests.request_condition_serializers import RequestTypeSerializer

logger = logging.getLogger(__name__)


class RequestTypeViewSet(BaseEntityViewSet):
    okta_endpoint = "/governance/api/v2/resources"
    entity_type = "request_types"
    serializer_class = RequestTypeSerializer
    model = RequestType

    def extract_data(self, okta_data):
        """Extract and format request type data from Okta response"""
        formatted_data = []

        # Check if okta_data is a list or single object
        items = okta_data if isinstance(okta_data, list) else [okta_data]

        for item in items:
            formatted_data.append({
                "requested": item.get("requested", {}),
                "requested_for": item.get("requestedFor", {}),
                "requester_field_values": item.get("requesterFieldValues", {})
            })

        logger.info("Extracted %d Request Type records", len(formatted_data))
        return formatted_data
