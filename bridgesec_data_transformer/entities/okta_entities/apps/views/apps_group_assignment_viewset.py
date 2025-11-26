import logging

import requests
from core.utils.okta_helpers import get_okta_headers
from core.utils.rate_limit import handle_rate_limit, rate_limit_headers
from django.conf import settings
from entities.okta_entities.apps.apps_models import AppGroupAssignment
from entities.okta_entities.apps.apps_serializers import \
    AppGroupAssignmentSerializer
from entities.okta_entities.apps.views.apps_base_viewset import BaseAppViewSet

logger = logging.getLogger(__name__)

class AppsGroupAssignmentViewSet(BaseAppViewSet):
    okta_endpoint = "/api/v1/apps/{appId}/groups"
    entity_type = "okta_app_group_assignment"
    serializer_class = AppGroupAssignmentSerializer
    model = AppGroupAssignment

    def fetch_from_okta(self, app_id, request=None):
        """
        Fetch group assignments for a specific app from Okta.
        """
        base_url = settings.OKTA_API_URL
        headers = get_okta_headers(request)

        # API call to get groups for this app
        groups_url = f"{base_url}/api/v1/apps/{app_id}/groups"
        logger.info(f"Fetching group assignments for app_id: {app_id}")

        response = requests.get(groups_url, headers=headers)

        if handle_rate_limit(response):
            logger.warning(f"Rate limit hit for app_id: {app_id}")
            return {"error": "Rate limit hit."}, 429, rate_limit_headers(response)

        if response.status_code != 200:
            logger.error(f"Failed to fetch groups for app {app_id}: {response.text}")
            return {"error": f"Failed to fetch groups: {response.text}"}, response.status_code, rate_limit_headers(response)

        group_data = response.json()
        logger.info(f"Fetched {len(group_data)} groups for app_id: {app_id}")

        return group_data, 200, rate_limit_headers(response)

    def extract_data(self, okta_data, app=None, request=None):
        """
        Formats group assignment data. Fetches group names for each group ID.
        """
        if not app:
            logger.warning("No app info provided for formatting")
            return []

        app_id = app.get("app_id")
        app_label = app.get("label", app_id)  # Use label if available, otherwise app_id

        base_url = settings.OKTA_API_URL
        headers = get_okta_headers(request)

        formatted_data = []
        for group in okta_data:
            group_id = group.get("id")
            group_name = None

            if group_id:
                group_url = f"{base_url}/api/v1/groups/{group_id}"
                try:
                    group_detail_resp = requests.get(group_url, headers=headers)

                    if group_detail_resp.status_code == 200:
                        group_detail = group_detail_resp.json()
                        group_name = group_detail.get("profile", {}).get("name")
                        logger.debug(f"Resolved group {group_id} to name: {group_name}")
                except Exception as e:
                    logger.warning(f"Failed to fetch group name for {group_id}: {e}")

            formatted_record = {
                "app_id": app_id,
                "group_id": group_id,
                "priority": group.get("priority", ""),
                "profile": group.get("profile", {}),
                "retain_assignment": group.get("retain_assignment", ""),
                "timeouts": {}
            }
            formatted_data.append(formatted_record)

        logger.info(f"Formatted {len(formatted_data)} group assignments for app: {app_label}")
        return formatted_data
