import logging

import requests
from django.conf import settings
from core.utils.okta_helpers import get_okta_headers
from core.utils.rate_limit import handle_rate_limit

from entities.okta_entities.apps.apps_models import AppPushGroup
from entities.okta_entities.apps.apps_serializers import AppPushGroupSerializer
from entities.okta_entities.apps.views.apps_base_viewset import BaseAppViewSet

logger = logging.getLogger(__name__)


class AppPushGroupsViewSet(BaseAppViewSet):
    okta_endpoint = "/api/v1/apps/{app_id}/pushGroups"
    entity_type = "okta_app_push_groups"
    serializer_class = AppPushGroupSerializer
    model = AppPushGroup

    def fetch_from_okta(self, app_id, request=None):
        if not app_id:
            logger.error("app_id is required to fetch push groups")
            return [], 400, {}

        url = f"{self.okta_base_url}{self.okta_endpoint.format(app_id=app_id)}"
        headers = get_okta_headers(request)

        while True:
            response = requests.get(url, headers=headers)

            if handle_rate_limit(response):
                continue

            if response.status_code == 200:
                return response.json() if response.text.strip() else [], 200, {}
            if response.status_code in (404, 400):
                return [], response.status_code, {}
            logger.warning(
                "Failed to fetch push groups for app %s: %s %s",
                app_id, response.status_code, response.text,
            )
            return [], response.status_code, {}

    def extract_data(self, okta_data, app_info=None):
        items = okta_data if isinstance(okta_data, list) else []
        app_id = app_info.get("app_id", "") if isinstance(app_info, dict) else ""
        formatted_data = []
        for item in items:
            if not isinstance(item, dict):
                logger.warning("Skipping invalid record (not a dict): %s", item)
                continue
            formatted_data.append({
                "push_group_id": item.get("id", ""),
                "app_id": app_id,
                "source_group_id": item.get("sourceGroupId", ""),
                "status": item.get("status", ""),
            })
        logger.info("Extracted %d Push Group records for app %s", len(formatted_data), app_id)
        return formatted_data
