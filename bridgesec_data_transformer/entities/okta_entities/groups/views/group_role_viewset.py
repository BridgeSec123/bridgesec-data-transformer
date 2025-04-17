import logging

import requests
from django.conf import settings
from entities.okta_entities.groups.group_models import GroupRole
from entities.okta_entities.groups.group_serializers import GroupRoleSerializer
from entities.okta_entities.groups.views.group_base_viewset import BaseGroupViewSet
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)

class GroupRoleViewSet(BaseGroupViewSet):
    """
    ViewSet to fetch and store group roles details from Okta.
    """
    okta_endpoint = "api/v1/groups/{group_id}/roles"
    entity_type = "group_roles"
    serializer_class = GroupRoleSerializer
    model = GroupRole
    
    def fetch_from_okta(self, group_id):
        """
        Fetch group roles details for a specific group from Okta.
        """
        if not group_id:
            logger.error("Group ID is required to fetch roles.")
            return []

        url = f"{settings.OKTA_API_URL}/{self.okta_endpoint.format(group_id=group_id)}"
        headers = {"Authorization": f"SSWS {settings.OKTA_API_TOKEN}"}

        logger.info(f"Fetching data from Okta API: {url}")
        
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            logger.info(f"Successfully fetched roles for group {group_id}")
            return response.json()
        else:
            logger.error(f"Failed to fetch group roles. Status Code: {response.status_code}, Response: {response.text}")
            return []

    def extract_data(self, okta_data, group_id):
        """
        Extract and format group role data from Okta response.
        """
        logger.info("Extracting group role data from Okta response.")

        extracted_roles = []
        for role in okta_data:
            role_type = role.get("type") or role.get("roleType")  # "type" is for standard roles, "roleType" for custom
            role_entry = {
                "group_id": group_id,
                "role_type": role_type,
                "disable_notifications": role.get("disableNotifications", False),
                "resource_set_id": role.get("resourceSetId"),
                "role_id": role.get("roleId"),
                "target_app_list": role.get("targetAppInstanceIds", []),
                "target_group_list": role.get("targetGroupIds", []),
            }
            extracted_roles.append(role_entry)

        logger.info(f"Extracted {len(extracted_roles)} group role entries.")
        return extracted_roles

    def list(self, request, *args, **kwargs):
        """Retrieve all records from MongoDB and return serialized data."""
        start_date, end_date = super().list(request, *args, **kwargs)

        if not start_date or not end_date:
            memberships = self.model.objects()
            logger.info("Retrieved %d group roles records from MongoDB", len(memberships))
        else:
            memberships = self.filter_by_date(start_date, end_date)      
            logger.info(f"Retrieved {len(memberships)} group roles between {start_date} and {end_date}")

        memberships_data = [
            {
                "group_id": membership.group_id,
                "user_id": membership.user_id,
                "user_email": membership.user_email,
            }
            for membership in memberships
        ]

        logger.info(f"Returning {len(memberships_data)} group roles.")
        return Response(memberships_data, status=status.HTTP_200_OK)