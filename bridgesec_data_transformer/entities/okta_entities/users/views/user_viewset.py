import logging

from entities.okta_entities.users.user_models import User
from entities.okta_entities.users.views.user_base_viewset import BaseUserViewSet
from entities.okta_entities.users.user_serializers import UserSerializer

logger = logging.getLogger(__name__)

class UserViewSet(BaseUserViewSet):
    okta_endpoint = "/api/v1/users"
    entity_type = "okta_users"
    serializer_class = UserSerializer
    model = User
    

    def extract_data(self, okta_data):
        """
        Override to format the user data by removing the "profile" key.
        """
        logger.info("Extracting data from Okta response")
        extracted_data = super().extract_data(okta_data)

        formatted_data = []
    
        for record in extracted_data:
            profile = record.get("profile", {})

            formatted_record={
                "id": record.get("id"),
                "first_name": profile.get("firstName", ""),
                "last_name": profile.get("lastName", ""),
                "mobile_phone": profile.get("mobilePhone", ""),
                "second_email": profile.get("secondEmail", ""),
                "login": profile.get("login", ""),
                "email": profile.get("email", ""),
            }
            formatted_data.append(formatted_record)
        logger.info("Extracted and formatted %d user records from Okta", len(formatted_data))  

        return formatted_data