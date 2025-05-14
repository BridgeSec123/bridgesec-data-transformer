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

    def extract_data(self, okta_data):
        extracted_data = super().extract_data(okta_data)
        formatted_data = []

        for record in extracted_data:
            formatted_record = {
                "name": record.get("name", ""),
                "display_name": record.get("displayName", ""),
                "description": record.get("description", "")
            }
            formatted_data.append(formatted_record)
        logger.info(f"Formatted {len(formatted_data)} user types.")
        return formatted_data
