import logging

from rest_framework import status
from rest_framework.response import Response

from entities.okta_entities.users.user_models import User
from entities.okta_entities.users.views.user_base_viewset import BaseUserViewSet
from entities.okta_entities.users.user_serializers import UserSerializer

logger = logging.getLogger(__name__)

class UserViewSet(BaseUserViewSet):
    # queryset = UserEntity.objects.all()
    okta_endpoint = "/api/v1/users"
    entity_type = "users"
    serializer_class = UserSerializer
    model = User
    
    def list(self, request, *args, **kwargs):
        """Retrieve all records from MongoDB and return the users data."""
        start_date, end_date = super().list(request, *args, **kwargs)

        if not start_date or not end_date:
            users = self.model.objects() # Fetch all documents using MongoEngine
            logger.info("Retrieved %d user records from MongoDB", len(users))

        else:
            users = self.filter_by_date(start_date, end_date)
            logger.info(f"Retrieved {len(users)} users between {start_date} and {end_date}")

        users_data = []
        for user in users:
            users_data.append(
                {
                    "user_id": user.id,
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

        formatted_data = []
        allowed_fields = set(User._fields.keys())

        for record in extracted_data:
            if "profile" in record and "id" in record:
                profile_data = record["profile"]
                profile_data["user_id"] = record["id"]

                # Filter only allowed fields + user_id
                filtered = {key: value for key, value in profile_data.items() if key in allowed_fields or key == "user_id"}
                formatted_data.append(filtered)

        logger.info("Final extracted %d user records after formatting and filtering", len(formatted_data))
        return formatted_data
