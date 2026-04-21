import logging

from entities.views.base_view import BaseEntityViewSet
from entities.okta_entities.requests.request_condition_models import RequestType
from entities.okta_entities.requests.request_condition_serializers import RequestTypeSerializer

logger = logging.getLogger(__name__)


class RequestTypeViewSet(BaseEntityViewSet):
    okta_endpoint = "/governance/api/v2/requests"
    entity_type = "request_types"
    serializer_class = RequestTypeSerializer
    model = RequestType

    def extract_data(self, okta_data):
        """Extract and format okta_request_v2 data from Okta response"""
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
            formatted_data.append({
                "request_id": item.get("id", ""),
                "requested": item.get("requested", {}),
                "requested_for": item.get("requestedFor", {}),
                "requester_field_values": item.get("requesterFieldValues", {}),
                "status": item.get("status", ""),
                "created": item.get("created", ""),
                "created_by": item.get("createdBy", ""),
                "last_updated": item.get("lastUpdated", ""),
                "last_updated_by": item.get("lastUpdatedBy", ""),
                "access_duration": item.get("accessDuration", ""),
                "granted": item.get("granted", ""),
                "grant_status": item.get("grantStatus", ""),
                "resolved": item.get("resolved", ""),
                "revocation_scheduled": item.get("revocationScheduled", ""),
                "revocation_status": item.get("revocationStatus", ""),
                "revoked": item.get("revoked", ""),
            })

        logger.info("Extracted %d Request (v2) records", len(formatted_data))
        return formatted_data
