import logging

import requests
from django.conf import settings
from entities.okta_entities.groups.group_models import GroupMember
from entities.okta_entities.groups.group_serializers import GroupMemberSerializer
from entities.okta_entities.groups.views.group_base_viewset import BaseGroupViewSet
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)

class GroupMembershipViewSet(BaseGroupViewSet):
    """
    ViewSet to fetch and store group membership details from Okta.
    """
    okta_endpoint = "api/v1/groups/{group_id}/users"
    entity_type = "group_memberships"
    serializer_class = GroupMemberSerializer
    model = GroupMember
    
    def fetch_from_okta(self, group_id):
        """
        Fetch group membership details for a specific group from Okta.
        """
        if not group_id:
            logger.error("Group ID is required to fetch memberships.")
            return []

        url = f"{settings.OKTA_API_URL}/{self.okta_endpoint.format(group_id=group_id)}"
        headers = {
            "Authorization": f"SSWS {settings.OKTA_API_TOKEN}",
            "Accept": "application/json"
        }

        logger.info(f"Fetching data from Okta API: {url}")
        
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            logger.info(f"Successfully fetched memberships for group {group_id}")
            return response.json()
        else:
            logger.error(f"Failed to fetch group memberships. Status Code: {response.status_code}, Response: {response.text}")
            return []
    

    def list(self, request, *args, **kwargs):
        """Retrieve all records from MongoDB and return serialized data."""
        start_date, end_date = super().list(request, *args, **kwargs)

        if not start_date or not end_date:
            memberships = self.model.objects()
            logger.info("Retrieved %d group membership records from MongoDB", len(memberships))
        else:
            memberships = self.filter_by_date(start_date, end_date)
            logger.info(f"Retrieved {len(memberships)} group memberships between {start_date} and {end_date}")

        memberships_data = [
            {
                "group_id": membership.group_id,
                "user_id": membership.user_id,
                "user_email": membership.user_email,
            }
            for membership in memberships
        ]

        logger.info(f"Returning {len(memberships_data)} group memberships.")
        return Response(memberships_data, status=status.HTTP_200_OK)

    def extract_data(self, okta_data, group_id):
        """
        Extract and format group membership data from Okta response.
        """
        logger.info("Extracting membership data from Okta response.")
        extracted_data = super().extract_data(okta_data)
        user_ids = [record.get("id", "") for record in extracted_data if "id" in record]

        # Structure data correctly
        formatted_data = [{
            "group_id": group_id,
            "users": user_ids
        }]
        
        return formatted_data