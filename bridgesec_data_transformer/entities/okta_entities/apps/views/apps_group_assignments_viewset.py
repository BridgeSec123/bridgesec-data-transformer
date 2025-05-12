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
        and group results by app_id.
        """
        base_url = settings.OKTA_API_URL
        headers = {"Authorization": f"SSWS {settings.OKTA_API_TOKEN}"}

        discovery_url = f"{base_url}/api/v1/apps"
        response = requests.get(discovery_url, headers=headers)

        if handle_rate_limit(response):
            logger.warning("Rate limit hit while fetching app IDs.")
            return {"error": "Rate limit hit."}, 429, rate_limit_headers(response)

        if response.status_code != 200:
            logger.error(f"Failed to fetch app list: {response.text}")
            return {"error": f"Failed to fetch apps: {response.text}"}, response.status_code, rate_limit_headers(response)

        apps = response.json()
        grouped_assignments = []

        logger.info(f"Found {len(apps)} apps. Fetching group assignments for each...")

        for app in apps:
            app_id = app.get("id")
            if not app_id:
                logger.warning("App without ID found. Skipping.")
                continue

            groups_url = f"{base_url}/api/v1/apps/{app_id}/groups"
            group_response = requests.get(groups_url, headers=headers)

            if handle_rate_limit(group_response):
                logger.warning(f"Rate limit hit while fetching groups for app {app_id}. Skipping.")
                continue

            if group_response.status_code != 200:
                logger.error(f"Failed to fetch group assignments for app {app_id}: {group_response.text}")
                continue

            group_data = group_response.json()
            logger.info(f"Fetched {len(group_data)} group assignments for app {app_id}.")

            grouped_assignments.append({
                "app_id": app_id,
                "group": group_data,
                "timeouts": {}
            })

        return grouped_assignments, 200, rate_limit_headers(response)

    def extract_data(self, okta_data):
        """
        Extracts and formats app_id, group, and timeouts fields from Okta response.
        """
        logger.info("Extracting data from Okta response")
        # extracted_data = super().extract_data(okta_data) or []

        formatted_data = []
        for record in okta_data:
            raw_groups = record.get("group", [])
            formatted_groups = []

            for group in raw_groups:
                group_obj = {
                    "id": group.get("id"),
                    "priority": group.get("priority")
                }

                # Include profile only if present
                profile = group.get("profile")
                if profile:
                    group_obj["profile"] = profile

                formatted_groups.append(group_obj)
            formatted_record = {
                "app_id": record.get("app_id"),
                "group": formatted_groups,  # List of group objects
                "timeouts": record.get("timeouts", {})
            }

            formatted_data.append(formatted_record)

        logger.info("Final extracted %d group assignment records after formatting and filtering", len(formatted_data))
        return formatted_data
