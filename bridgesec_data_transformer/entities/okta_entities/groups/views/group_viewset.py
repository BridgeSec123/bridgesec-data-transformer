import logging

from entities.okta_entities.groups.group_models import Group
from entities.okta_entities.groups.views.group_base_viewset import BaseGroupViewSet
from entities.okta_entities.groups.group_serializers import GroupSerializer
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)

class GroupEntityViewSet(BaseGroupViewSet):
    okta_endpoint = "/api/v1/groups"
    entity_type = "groups"
    serializer_class = GroupSerializer
    model = Group
    
    def list(self, request, *args, **kwargs):
        """Retrieve all records from MongoDB and return serialized data."""
        start_date, end_date = super().list(request, *args, **kwargs)

        if not start_date or not end_date:
            groups = self.model.objects()  # Fetch all documents using MongoEngine
            logger.info("Retrieved %d groups records from MongoDB", len(groups))

        else:
            groups = self.filter_by_date(start_date, end_date)
            logger.info(f"Retrieved {len(groups)} groups between {start_date} and {end_date}")

        groups_data = []
        for group in groups:
            group_data = {
                "name": group.name,
                "description": group.description,
            }
            if group.custom_profile_attributes:
                group_data["custom_profile_attributes"] = group.custom_profile_attributes

            groups_data.append(group_data)

        logger.info(f"Returning {len(groups_data)} groups.")
        return Response(groups_data, status=status.HTTP_200_OK)
    
    def extract_data(self, okta_data):
        logger.info("Extracting data from Okta response.")
        extracted_data = super().extract_data(okta_data)

        # Flatten the data by removing the "profile" key
        formatted_data = []
        for record in extracted_data:
            if "profile" in record:
                profile = record["profile"]
                # changes here
                modified_profile = {
                    "okta_group_id": record.get("id"),
                    "name": profile.get("name", ""),
                    "description": profile.get("description", ""),
                }
                scopes = profile.get("scopes", [])
                if scopes:
                    modified_profile["custom_profile_attributes"] = {"scopes": scopes}
                formatted_data.append(modified_profile)
                
        logger.info(f"Extracted and formatted {len(formatted_data)} group records from Okta.")
        return formatted_data