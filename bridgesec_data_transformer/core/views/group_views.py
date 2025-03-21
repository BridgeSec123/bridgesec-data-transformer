import logging

from rest_framework import status
from rest_framework.response import Response

from core.models.group_models import Group
from core.serializers.group_serializers import GroupSerializer
from core.views.base import BaseViewSet

logger = logging.getLogger(__name__)

class GroupViewSet(BaseViewSet):
    queryset = Group.objects.all()
    okta_endpoint = "/api/v1/groups"
    entity_type = "groups"
    serializer_class = GroupSerializer
    model = Group
    
    def list(self, request, *args, **kwargs):
        """Retrieve all records from MongoDB and return serialized data."""
        if not self.model or not self.serializer_class:
            logger.error("Model or serializer_class is not defined in GroupViewSet.")
            return Response({"error": "Model or serializer_class not defined"}, status=status.HTTP_400_BAD_REQUEST)

        groups = self.model.objects()  # Fetch all documents using MongoEngine
        logger.info("Retrieved %d user records from MongoDB", len(groups))
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
        """
        Override to format the user data by removing the "profile" key.
        """
        logger.info("Extracting data from Okta response.")
        extracted_data = super().extract_data(okta_data)

        # Flatten the data by removing the "profile" key
        formatted_data = []
        for record in extracted_data:
            if "profile" in record:
                profile = record["profile"]
                modified_profile = {
                    "name": profile.get("name", ""),
                    "description": profile.get("description", ""),
                }
                scopes = profile.get("scopes", [])
                if scopes:
                    modified_profile["custom_profile_attributes"] = {"scopes": scopes}
                formatted_data.append(modified_profile)
                
        logger.info(f"Extracted and formatted {len(formatted_data)} group records from Okta.")
        return formatted_data