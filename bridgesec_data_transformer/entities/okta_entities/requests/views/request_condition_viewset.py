import logging

from entities.views.base_view import BaseEntityViewSet
from entities.okta_entities.requests.request_condition_models import RequestCondition
from entities.okta_entities.requests.request_condition_serializers import RequestConditionSerializer

logger = logging.getLogger(__name__)


class RequestConditionViewSet(BaseEntityViewSet):
    okta_endpoint = "/governance/api/v2/resources"
    entity_type = "request_conditions"
    serializer_class = RequestConditionSerializer
    model = RequestCondition

    def extract_data(self, okta_data):
        """Extract and format request condition data from Okta response"""
        formatted_data = []

        # Check if okta_data is a list or single object
        items = okta_data if isinstance(okta_data, list) else [okta_data]

        for item in items:
            formatted_data.append({
                "resource_id": item.get("resourceId", ""),
                "approval_sequence_id": item.get("approvalSequenceId", ""),
                "name": item.get("name", ""),
                "access_scope_settings": item.get("accessScopeSettings", []),
                "requester_settings": item.get("requesterSettings", []),
                "description": item.get("description", ""),
                "priority": item.get("priority"),
                "access_duration_settings": item.get("accessDurationSettings", [])
            })

        logger.info("Extracted %d Request Condition records", len(formatted_data))
        return formatted_data
