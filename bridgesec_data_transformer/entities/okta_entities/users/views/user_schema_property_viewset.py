import logging

from rest_framework import status
from rest_framework.response import Response

from entities.okta_entities.users.user_models import UserSchemaProperty
from entities.okta_entities.users.user_serializers import UserSchemaPropertySerializer
from entities.okta_entities.users.views.user_base_viewset import BaseUserViewSet

logger = logging.getLogger(__name__)

class UserSchemaPropertyViewSet(BaseUserViewSet):
    # queryset = UserType.objects.all()
    okta_endpoint = "/api/v1/meta/schemas/user/default"
    entity_type = "user_schema_properties"
    serializer_class = UserSchemaPropertySerializer
    model = UserSchemaProperty
    
    def list(self, request, *args, **kwargs):
        """Retrieve all records from MongoDB and return serialized data."""
        start_date, end_date = super().list(request, *args, **kwargs)

        if not start_date or not end_date:
            user_types = self.model.objects()  # Fetch all documents using MongoEngine
            logger.info("Retrieved %d user records from MongoDB", len(user_types))

        else:
            user_types = self.filter_by_date(start_date, end_date)
            logger.info(f"Retrieved {len(user_types)} user types between {start_date} and {end_date}")

        user_types_data = []
        for user_type in user_types:
            user_type_data = {
                "name": user_type.name,
                "display_name": user_type.displayName,
                "description": user_type.description,
            } 

            user_types_data.append(user_type_data)
        logger.info(f"Returning {len(user_types_data)} user types.")
        return Response(user_types_data, status=status.HTTP_200_OK)

    def extract_data(self, okta_data):
        # return super().extract_data(okta_data)
        login = okta_data.get("definitions").get("base").get("properties").get("login")
        formatted_data = [{
            "index": okta_data.get("name"),
            "title": okta_data.get("title"),
            "type": okta_data.get("type"),
            "description": okta_data.get("description"),
            "master": login.get("master").get("type"),
            "scope": login.get("scope")
        }]
        return formatted_data
