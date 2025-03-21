import logging

from rest_framework import status
from rest_framework.response import Response

from core.models.user_models import UserProfile
from core.serializers.user_serializers import UserSerializer
from core.views.base import BaseViewSet

logger = logging.getLogger(__name__)

class UserViewSet(BaseViewSet):
    queryset = UserProfile.objects.all()
    okta_endpoint = "/api/v1/users"
    entity_type = "users"
    serializer_class = UserSerializer
    model = UserProfile
    
    def list(self, request, *args, **kwargs):
        """Retrieve all records from MongoDB and return the users data."""
        if not self.model or not self.serializer_class:
            logger.error("Model or serializer_class is not defined in UserViewSet.")
            return Response({"error": "Model or serializer_class not defined"}, status=status.HTTP_400_BAD_REQUEST)

        users = self.model.objects()  # Fetch all documents using MongoEngine
        logger.info("Retrieved %d user records from MongoDB", len(users))
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
            
        logger.info("Returning %d users", len(users_data))
        return Response(users_data, status=status.HTTP_200_OK)

    def extract_data(self, okta_data):
        """
        Override to format the user data by removing the "profile" key.
        """
        logger.info("Extracting data from Okta response")
        extracted_data = super().extract_data(okta_data)

        formatted_data = [record.get("profile", {}) for record in extracted_data if "profile" in record]
        logger.info("Extracted and formatted %d user records from Okta", len(formatted_data))
        
        return formatted_data
