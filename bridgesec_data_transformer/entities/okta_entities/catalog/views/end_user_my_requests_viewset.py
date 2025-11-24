import logging

from entities.views.base_view import BaseEntityViewSet
from entities.okta_entities.catalog.catalog_models import EndUserMyRequests
from entities.okta_entities.catalog.catalog_serializers import EndUserMyRequestsSerializer

logger = logging.getLogger(__name__)


class EndUserMyRequestsViewSet(BaseEntityViewSet):
    okta_endpoint = "/governance/api/v2/catalogs/default/user"
    entity_type = "end_user_my_requests"
    serializer_class = EndUserMyRequestsSerializer
    model = EndUserMyRequests

    def extract_data(self, okta_data):
        """Extract and format end user my requests data from Okta response"""
        formatted_data = []

        # Check if okta_data is a list or single object
        items = okta_data if isinstance(okta_data, list) else [okta_data]

        for item in items:
            formatted_data.append({
                "entry_id": item.get("entryId", ""),
                "id": item.get("id", ""),
                "requester_field_values": item.get("requesterFieldValues", [])
            })

        logger.info("Extracted %d End User My Requests records", len(formatted_data))
        return formatted_data
