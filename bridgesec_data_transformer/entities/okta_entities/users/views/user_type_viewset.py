import logging

from rest_framework import status
from rest_framework.response import Response

from entities.okta_entities.users.user_models import UserType
from entities.okta_entities.users.user_serializers import UserTypeSerializer
from entities.okta_entities.users.views.user_base_viewset import BaseUserViewSet

logger = logging.getLogger(__name__)

class UserTypeViewSet(BaseUserViewSet):
    # queryset = UserType.objects.all()
    okta_endpoint = "/api/v1/meta/types/user"
    entity_type = "user_types"
    serializer_class = UserTypeSerializer
    model = UserType
    
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