from core.views.base import BaseViewSet
from core.serializers.user_serializers import UserSerializer
from core.models.user_models import UserProfile
from rest_framework.response import Response
from rest_framework import status

class UserViewSet(BaseViewSet):
    queryset = UserProfile.objects.all()
    okta_endpoint = "/api/v1/users"
    entity_type = "users"
    serializer_class = UserSerializer
    model = UserProfile
    
    def list(self, request, *args, **kwargs):
        """Retrieve all records from MongoDB and return serialized data."""
        if not self.model or not self.serializer_class:
            return Response({"error": "Model or serializer_class not defined"}, status=status.HTTP_400_BAD_REQUEST)

        users = self.model.objects()  # Fetch all documents using MongoEngine
        users_data = []
        for user in users:
            users_data.append(
                {
                    "first_name": user.firstName,
                    "last_name": user.lastName,
                    "mobile_phone": user.mobilePhone,
                    "second_email": user.secondEmail,
                    "login": user.login,
                    "email": user.email,
                }
            )
        
        return Response(users_data, status=status.HTTP_200_OK)

    def extract_data(self, okta_data):
        """
        Override to format the user data by removing the "profile" key.
        """
        extracted_data = super().extract_data(okta_data)

        # Flatten the data by removing the "profile" key
        formatted_data = [record.get("profile", {}) for record in extracted_data if "profile" in record]
        return formatted_data
