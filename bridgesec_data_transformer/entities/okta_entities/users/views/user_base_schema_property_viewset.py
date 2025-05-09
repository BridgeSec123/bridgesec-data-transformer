import logging

from entities.okta_entities.users.user_models import UserBaseSchemaProperty
from entities.okta_entities.users.user_serializers import UserBaseSchemaPropertySerializer
from entities.okta_entities.users.views.user_base_viewset import BaseUserViewSet

logger = logging.getLogger(__name__)

class UserBaseSchemaPropertyViewSet(BaseUserViewSet):
    okta_endpoint = "/api/v1/meta/schemas/user/default"
    entity_type = "user_base_schema_properties"
    serializer_class = UserBaseSchemaPropertySerializer
    model = UserBaseSchemaProperty
    
    
    def extract_data(self, okta_data):
        login = okta_data.get("definitions").get("base").get("properties").get("login")
        user_type = okta_data.get("_links", {}).get("self", {}).get("href", "")
        user_type_id = user_type.rsplit("/", 1)[-1] if user_type else ""

        formatted_data = [{
            "index": okta_data.get("name", ""),
            "title": okta_data.get("title", ""),
            "type": okta_data.get("type", ""),
            "master": login.get("master").get("type", ""),  
            "permissions": login.get("permissions", ""),
            "pattern": okta_data.get("pattern", ""),
            "required": okta_data.get("required", ""),
            "user_type": user_type_id
        }]
        return formatted_data
