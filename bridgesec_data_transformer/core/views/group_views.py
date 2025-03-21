from core.views.base import BaseViewSet
from core.serializers.group_serializers import GroupSerializer
from core.models.group_models import Group
from rest_framework.response import Response
from rest_framework import status

class GroupViewSet(BaseViewSet):
    queryset = Group.objects.all()
    okta_endpoint = "/api/v1/groups"
    entity_type = "groups"
    serializer_class = GroupSerializer
    model = Group
    
    def list(self, request, *args, **kwargs):
        """Retrieve all records from MongoDB and return serialized data."""
        if not self.model or not self.serializer_class:
            return Response({"error": "Model or serializer_class not defined"}, status=status.HTTP_400_BAD_REQUEST)

        groups = self.model.objects()  # Fetch all documents using MongoEngine
        groups_data = []
        for group in groups:
            groups_data.append(
                {
                    "name": group.name,
                    "description": group.description,
                }
            )
            if group.custom_profile_attributes:
                groups_data[-1]["custom_profile_attributes"] = group.custom_profile_attributes
        
        return Response(groups_data, status=status.HTTP_200_OK)
    
    def extract_data(self, okta_data):
        """
        Override to format the user data by removing the "profile" key.
        """
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

        return formatted_data