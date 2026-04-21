import logging

import requests as http_requests
from django.conf import settings

from core.utils.okta_helpers import get_okta_headers
from entities.views.base_view import BaseEntityViewSet
from entities.okta_entities.requests.request_condition_models import RequestCondition
from entities.okta_entities.requests.request_condition_serializers import RequestConditionSerializer

logger = logging.getLogger(__name__)


class RequestConditionViewSet(BaseEntityViewSet):
    okta_endpoint = "/governance/api/v2/resources/{resource_id}/access-request-settings/conditions"
    resources_endpoint = "/governance/api/v2/resources"
    entity_type = "request_conditions"
    serializer_class = RequestConditionSerializer
    model = RequestCondition

    def fetch_and_store_data(self, db_name, request=None):
        try:
            headers = get_okta_headers(request)
            resources_url = f"{settings.OKTA_API_URL}{self.resources_endpoint}"

            res = http_requests.get(resources_url, headers=headers)
            if res.status_code != 200:
                logger.error("Failed to fetch resources: %s", res.text)
                return {"error": "Failed to fetch resources"}

            raw = res.json()
            resources = raw if isinstance(raw, list) else raw.get("value", [])

            all_conditions = []
            for resource in resources:
                resource_id = resource.get("id", "")
                if not resource_id:
                    continue

                conditions_url = (
                    f"{settings.OKTA_API_URL}/governance/api/v2/resources/"
                    f"{resource_id}/access-request-settings/conditions"
                )
                cond_res = http_requests.get(conditions_url, headers=headers)
                if cond_res.status_code != 200:
                    logger.warning("Failed to fetch conditions for resource %s: %s", resource_id, cond_res.text)
                    continue

                cond_raw = cond_res.json()
                conditions = self.extract_data(cond_raw, resource_id=resource_id)
                all_conditions.extend(conditions)

            self.store_data(all_conditions, db_name=db_name)
            logger.info("Stored %d Request Condition records in %s", len(all_conditions), db_name)
            return {"okta_request_conditions": all_conditions}

        except Exception as e:
            logger.error("Error in RequestConditionViewSet.fetch_and_store_data: %s", str(e), exc_info=True)
            return {"error": str(e)}

    def extract_data(self, okta_data, resource_id=""):
        """Extract and format request condition data from Okta response"""
        if isinstance(okta_data, dict):
            items = okta_data.get("value", okta_data.get("conditions", []))
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
                "condition_id": item.get("id", ""),
                "resource_id": resource_id or item.get("resourceId", ""),
                "approval_sequence_id": item.get("approvalSequenceId", ""),
                "name": item.get("name", ""),
                "status": item.get("status", ""),
                "priority": item.get("priority"),
                "description": item.get("description", ""),
                "created": item.get("created", ""),
                "created_by": item.get("createdBy", ""),
                "last_updated": item.get("lastUpdated", ""),
                "last_updated_by": item.get("lastUpdatedBy", ""),
                "access_scope_settings": item.get("accessScopeSettings", []),
                "requester_settings": item.get("requesterSettings", []),
                "access_duration_settings": item.get("accessDurationSettings", []),
            })

        logger.info("Extracted %d Request Condition records", len(formatted_data))
        return formatted_data
