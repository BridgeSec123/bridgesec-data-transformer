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
                "city": record.get("city", ""),
                "cost_center": record.get("costCenter", ""),
                "country_code": record.get("countryCode", ""),
                "custom_profile_properties": record.get("customProfileProperties", {}),
                "custom_profile_properties_to_ignore": record.get("customProfilePropertiesToIgnore", []),
                "department": record.get("department", ""),
                "display_name": record.get("displayName", ""),
                "division": record.get("division", ""),
                "employee_number": record.get("employeeNumber", ""),
                "expire_password_on_create": record.get("expirePasswordOnCreate", None),
                "honorofix_prefix": record.get("honorofixPrefix", ""),
                "honorofix_suffix": record.get("honorofixSuffix", ""),
                "locale": record.get("locale", ""),
                "manager": record.get("manager", ""),
                "manager_id": record.get("managerId", ""),
                "middle_name": record.get("middleName", ""),
                "nick_name": profile.get("nickname", ""),
                "old_password": record.get("oldPassword", ""),
                "organization": record.get("organization", ""),
                "password": record.get("password", ""),
                "password_inline_hook": record.get("passwordInlineHook", ""),
                "password_hash": record.get("passwordHash", []),
                "postal_address": record.get("postalAddress", ""),
                "preferred_language": record.get("preferredLanguage", ""),
                "primary_phone": record.get("primaryPhone", ""),
                "profile_url": record.get("profileUrl", ""),
                "recovery_answer": record.get("recoveryAnswer", ""),
                "recovery_question": record.get("recoveryQuestion", ""),
                "state": record.get("state", ""),
                "status": record.get("status", ""),
                "street_address": record.get("streetAddress", ""),
                "timezone": record.get("timezone", ""),
                "title": record.get("title", ""),
                "user_type": record.get("userType", ""),
                "zip_code": record.get("zipCode", ""),
            }
            formatted_data.append(formatted_record)
        logger.info("Extracted and formatted %d user records from Okta", len(formatted_data))  

        return formatted_data