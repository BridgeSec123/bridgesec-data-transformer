from core.views.base import BaseViewSet
from core.serializers.user_serializers import UserSerializer
from core.models.user_models import UserProfile
from rest_framework.response import Response

class UserViewSet(BaseViewSet):
    queryset = UserProfile.objects.all()
    okta_endpoint = "/api/v1/users"
    entity_type = "users"
    serializer_class = UserSerializer
    model = UserProfile

    def extract_data(self, okta_data):
        """
        Override to format the user data by removing the "profile" key.
        """
        extracted_data = super().extract_data(okta_data)

        # Flatten the data by removing the "profile" key
        formatted_data = [record.get("profile", {}) for record in extracted_data if "profile" in record]
        return formatted_data
