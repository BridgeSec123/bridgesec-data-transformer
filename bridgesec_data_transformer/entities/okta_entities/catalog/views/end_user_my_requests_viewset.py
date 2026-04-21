import logging

from entities.views.base_view import BaseEntityViewSet
from entities.okta_entities.catalog.catalog_models import EndUserMyRequests
from entities.okta_entities.catalog.catalog_serializers import EndUserMyRequestsSerializer

logger = logging.getLogger(__name__)


class EndUserMyRequestsViewSet(BaseEntityViewSet):
    okta_endpoint = "/governance/api/v2/requests"
    entity_type = "end_user_my_requests"
    serializer_class = EndUserMyRequestsSerializer
    model = EndUserMyRequests

    def extract_data(self, okta_data):
        """Extract and format end user my requests data from Okta response"""
        if isinstance(okta_data, dict):
            items = okta_data.get("value", okta_data.get("requests", []))
        elif isinstance(okta_data, list):
            items = okta_data
        else:
            items = []

        formatted_data = []
        for item in items:
            if not isinstance(item, dict):
                logger.warning("Skipping invalid record (not a dict): %s", item)
                continue

            raw_values = item.get("requesterFieldValues", [])
            requester_field_values = [
                {
                    "id": v.get("id", ""),
                    "label": v.get("label", ""),
                    "type": v.get("type", ""),
                    "value": str(v.get("value", "")),
                    "values": v.get("values", []),
                }
                for v in (raw_values if isinstance(raw_values, list) else [])
                if isinstance(v, dict)
            ]

            formatted_data.append({
                "request_id": item.get("id", ""),
                "entry_id": item.get("entryId", ""),
                "status": item.get("status", ""),
                "requester_field_values": requester_field_values,
            })

        logger.info("Extracted %d End User My Requests records", len(formatted_data))
        return formatted_data
