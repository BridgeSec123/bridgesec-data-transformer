import logging

import requests
from core.utils.okta_helpers import get_okta_headers
from core.utils.rate_limit import handle_rate_limit
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

    def get_user_names_from_ids(self, user_ids, request=None):
        """
        Fetch user names by making API calls for each user ID.
        Optimized to handle large batches efficiently.
        """
        if not user_ids:
            return []

        user_names = []
        headers = get_okta_headers(request)

        # Log the number of users to process
        logger.info(f"Processing {len(user_ids)} users to fetch names")

        # Process in batches to avoid too many sequential API calls
        batch_size = 50  # Process 50 users at a time

        for i in range(0, len(user_ids), batch_size):
            batch = user_ids[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1} of {(len(user_ids) + batch_size - 1)//batch_size}")

            for user_id in batch:
                try:
                    user_url = f"{self.okta_base_url}/api/v1/users/{user_id}"
                    response = requests.get(user_url, headers=headers)
                    if response.status_code == 200:
                        user_data = response.json()
                        # Try to get firstName as primary, then display name, email, or login as fallback
                        user_name = (user_data.get("profile", {}).get("firstName") or
                                   user_data.get("profile", {}).get("displayName") or
                                   user_data.get("profile", {}).get("email") or
                                   user_data.get("profile", {}).get("login") or
                                   user_data.get("login", ""))
                        if user_name:
                            user_names.append(user_name)
                        else:
                            logger.warning(f"No name found for user ID {user_id}")
                            user_names.append(user_id)
                    else:
                        logger.warning(f"Failed to fetch user details for ID {user_id}")
                        user_names.append(user_id)
                except Exception as e:
                    logger.error(f"Error fetching user details for ID {user_id}: {e}")
                    user_names.append(user_id)

        logger.info(f"Successfully processed {len(user_names)} user names")
        return user_names

    def fetch_from_okta(self, group_id, request=None):
        """
        Fetch group membership details for a specific group from Okta.
        """
        if not group_id:
            logger.error("Group ID is required to fetch memberships.")
            return []

        url = f"{self.okta_base_url}/{self.okta_endpoint.format(group_id=group_id)}"
        headers = get_okta_headers(request)

        logger.info(f"Fetching data from Okta API: {url}")

        while True:
            response = requests.get(url, headers=headers)

            if handle_rate_limit(response):
                continue

            if response.status_code == 200:
                logger.info(f"Successfully fetched memberships for group {group_id}")
                return response.json()
            logger.error(f"Failed to fetch group memberships. Status Code: {response.status_code}, Response: {response.text}")
            return []
    
    def extract_data(self, okta_data, group_id):
        """
        Extract and format group membership data from Okta response.
        """
        logger.info("Extracting membership data from Okta response.")
        extracted_data = super().extract_data(okta_data)
        user_ids = [record.get("id", "") for record in extracted_data if "id" in record]

        # Convert user IDs to user names
        # user_names = self.get_user_names_from_ids(user_ids)

        # Structure data correctly
        formatted_data = [{
            "group_id": group_id,
            "users": user_ids
        }]
        
        return formatted_data