import logging

import requests
from core.utils.rate_limit import handle_rate_limit, rate_limit_headers
from django.conf import settings

from entities.okta_entities.apps.apps_models import AppGroupAssignments
from entities.okta_entities.apps.apps_serializers import AppGroupAssignmentsSerializer
from entities.okta_entities.apps.views.apps_base_viewset import BaseAppViewSet

logger = logging.getLogger(__name__)

class AppsGroupAssignmentsViewSet(BaseAppViewSet):  
    okta_endpoint = "/api/v1/apps/{appId}/groups"
    entity_type = "okta_apps_group_assignments"
    serializer_class = AppGroupAssignmentsSerializer
    model = AppGroupAssignments

    def fetch_from_okta(self):
        """
        Fetch all Okta apps, then fetch group assignments for each app,
        replace app_id with app label, group.id with group name.
        """
        base_url = settings.OKTA_API_URL
        headers = {"Authorization": f"SSWS {settings.OKTA_API_TOKEN}"}

        # Step 1: fetch all apps
        discovery_url = f"{base_url}/api/v1/apps"
        response = requests.get(discovery_url, headers=headers)

        if handle_rate_limit(response):
            return {"error": "Rate limit hit."}, 429, rate_limit_headers(response)

        if response.status_code != 200:
            return {"error": f"Failed to fetch apps: {response.text}"}, response.status_code, rate_limit_headers(response)

        apps = response.json()
        grouped_assignments = []

        for app in apps:
            app_id = app.get("id")
            app_label = app.get("label")  # <-- store label instead of id
            if not app_id or not app_label:
                continue

            # Step 2: fetch groups for this app
            groups_url = f"{base_url}/api/v1/apps/{app_id}/groups"
            group_response = requests.get(groups_url, headers=headers)

            if handle_rate_limit(group_response):
                continue
            if group_response.status_code != 200:
                continue

            group_data = group_response.json()
            formatted_groups = []

            # Step 3: resolve each groupId -> groupName
            for group in group_data:
                group_id = group.get("id")
                group_name = None

                if group_id:
                    group_url = f"{base_url}/api/v1/groups/{group_id}"
                    group_detail_resp = requests.get(group_url, headers=headers)

                    if group_detail_resp.status_code == 200:
                        group_detail = group_detail_resp.json()
                        group_name = group_detail.get("profile", {}).get("name")

                formatted_groups.append({
                    "id": group_name or group_id,  # replace with name if available
                    "priority": group.get("priority"),
                    "profile": group.get("profile", "")
                })

            grouped_assignments.append({
                "app_id": app_label,      # <-- use label here
                "group": formatted_groups,
                "timeouts": {}
            })

        return grouped_assignments, 200, rate_limit_headers(response)

    def extract_data(self, okta_data):
        """
        Extracts and formats app_id, group, and timeouts fields from Okta response.
        (Here we already map app_id -> label and group.id -> name in fetch_from_okta)
        """
        return okta_data
