import logging

import requests
from core.utils.rate_limit import handle_rate_limit, rate_limit_headers
from django.conf import settings

from entities.okta_entities.apps.apps_models import AppGroupAssignment
from entities.okta_entities.apps.apps_serializers import AppGroupAssignmentSerializer
from entities.okta_entities.apps.views.apps_base_viewset import BaseAppViewSet

logger = logging.getLogger(__name__)


class AppsGroupAssignmentViewSet(BaseAppViewSet):  
    okta_endpoint = "/api/v1/apps/{appId}/groups"
    entity_type = "okta_apps_group_assignment"
    serializer_class = AppGroupAssignmentSerializer
    model = AppGroupAssignment

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
        Extracts and flattens data from Okta response to match expected serializer format:
        - One entry per group
        - Fields: app_id, group_id, priority (dict), profile, retain_assignment, timeouts (list)
        """
        logger.info("Extracting data from Okta response")

        formatted_data = []

        for record in okta_data:
            app_id = record.get("app_id")
            raw_groups = record.get("group", [])

            for group in raw_groups:
                formatted_record = {
                    "app_id": app_id,
                    "group_id": group.get("id"),
                    "priority": group.get("priority", ""),  
                    "profile": group.get("profile", {}),
                    "retain_assignment": group.get("retain_assignment", ""), 
                    "timeouts": record.get("timeouts", {})
                }
                

                formatted_data.append(formatted_record)

        logger.info("Final extracted %d group assignment records after formatting and flattening", len(formatted_data))
        return formatted_data
