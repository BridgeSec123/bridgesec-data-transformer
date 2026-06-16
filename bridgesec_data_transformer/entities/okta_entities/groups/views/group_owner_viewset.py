import logging

import requests
from core.utils.okta_helpers import get_okta_headers
from core.utils.rate_limit import handle_rate_limit
from django.conf import settings
from entities.okta_entities.groups.group_models import GroupOwner
from entities.okta_entities.groups.group_serializers import GroupOwnerSerializer
from entities.okta_entities.groups.views.group_base_viewset import BaseGroupViewSet
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class GroupOwnerViewSet(BaseGroupViewSet):
    """
    ViewSet to fetch and store group owner details from Okta.
    """

    okta_endpoint = "api/v1/groups/{group_id}/owners"
    entity_type = "okta_group_owners"
    serializer_class = GroupOwnerSerializer
    model = GroupOwner

    def fetch_from_okta(self, group_id, request=None):
        """
        Fetch group owners details for a specific group from Okta.
        """
        if not group_id:
            logger.error("Group ID is required to fetch owners.")
            return []

        url = f"{self.okta_base_url}/{self.okta_endpoint.format(group_id=group_id)}"
        headers = get_okta_headers(request)

        logger.info(f"Fetching data from Okta API: {url}")

        while True:
            response = requests.get(url, headers=headers)

            if handle_rate_limit(response):
                continue

            if response.status_code == 200:
                logger.info(f"Successfully fetched owners for group {group_id}")
                return response.json()
            logger.error(
                f"Failed to fetch group owners. Status Code: {response.status_code}, Response: {response.text}"
            )
            return []

    def extract_data(self, okta_data, group_id):
        """
        Extract and format group owner data from Okta response.
        """
        logger.info("Extracting owner data from Okta response.")
        extracted_data = super().extract_data(okta_data)

        formatted_data = []
        for record in extracted_data:

            formatted_record = {
                "group_id": group_id,
                "id_of_group_owner": record.get("id"),
                "type": record.get("type"),
                "display_name": record.get("profile", {}).get("displayName"),
                "origin_id": record.get("profile", {}).get("originId"),
                "origin_type": record.get("profile", {}).get("originType"),
                "resolved": record.get("profile", {}).get("resolved"),
            }
            formatted_data.append(formatted_record)

        logger.info(
            "Extracted and formatted %d apps oauth records from Okta",
            len(formatted_data),
        )
        return formatted_data
