import logging

import requests
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
    entity_type = "group_owners"
    serializer_class = GroupOwnerSerializer
    model = GroupOwner
    
    def fetch_from_okta(self, group_id):
        """
        Fetch group owners details for a specific group from Okta.
        """
        if not group_id:
            logger.error("Group ID is required to fetch owners.")
            return []

        url = f"{settings.OKTA_API_URL}/{self.okta_endpoint.format(group_id=group_id)}"
        headers = {"Authorization": f"{settings.OKTA_API_TOKEN}"}

        logger.info(f"Fetching data from Okta API: {url}")
        
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            logger.info(f"Successfully fetched owners for group {group_id}")
            return response.json()
        else:
            logger.error(f"Failed to fetch group owners. Status Code: {response.status_code}, Response: {response.text}")
            return []
    
    def extract_data(self, okta_data, group_id):
        """
        Extract and format group owner data from Okta response.
        """
        logger.info("Extracting owner data from Okta response.")
        extracted_data = super().extract_data(okta_data)
        user_ids = [record.get("id", "") for record in extracted_data if "id" in record]

        # Structure data correctly
        formatted_data = {
            "group_id": group_id,
            "users": user_ids
        }
        
        return formatted_data