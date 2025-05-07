import logging

from rest_framework import status
from rest_framework.response import Response

from entities.okta_entities.users.user_models import UserSchemaProperty
from entities.okta_entities.users.user_serializers import UserSchemaPropertySerializer
from entities.okta_entities.users.views.user_base_viewset import BaseUserViewSet

logger = logging.getLogger(__name__)

class UserSchemaPropertyViewSet(BaseUserViewSet):
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
        user_type = okta_data.get("_links", {}).get("self", {}).get("href", "")
        user_type_id = user_type.rsplit("/", 1)[-1] if user_type else ""


        for prop in okta_data.get("definitions").get("base").get("properties"):
            if prop == "login":
                continue


        formatted_data = [{
            "index": okta_data.get("name"),
            "title": okta_data.get("title"),
            "type": okta_data.get("type"),
            "master": login.get("master").get("type"),
            "permissions": login.get("permissions"),
            "scope": login.get("scope"),
            "user_type": user_type_id,
            "array_enum": okta_data.get("arrayEnum"),
            "array_one_of": okta_data.get("arrayOneOf", ""),
            "array_type": okta_data.get("arrayType", ""),
            "enum": okta_data.get("enum", ""),
            "external_name": okta_data.get("externalName", ""),
            "external_namespace": okta_data.get("externalNamespace", ""),
            "master_override_priority": okta_data.get("masterOverridePriority", ""),
            "max_length": login.get("maxLength", ""),
            "min_length": login.get("minLength", ""),
            "one_of": okta_data.get("oneOf", ""),
            "pattern": okta_data.get("pattern", ""),
            "required": okta_data.get("required", ""),
            "unique": okta_data.get("unique", "")
        }]
        return formatted_data
