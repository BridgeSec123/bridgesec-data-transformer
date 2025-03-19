from core.views.base import BaseViewSet
from core.serializers.group_serializers import GroupSerializer
from core.models.group_models import Group

class GroupViewSet(BaseViewSet):
    queryset = Group.objects.all()
    okta_endpoint = "/api/v1/groups"
    entity_type = "groups"
    serializer_class = GroupSerializer
    model = Group
    
    def extract_data(self, okta_data):
        """
        Override to format the user data by removing the "profile" key.
        """
        extracted_data = super().extract_data(okta_data)

        # Flatten the data by removing the "profile" key
        formatted_data = [record.get("profile", {}) for record in extracted_data if "profile" in record]
        return formatted_data