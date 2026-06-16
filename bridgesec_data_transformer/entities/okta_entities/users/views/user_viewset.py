import logging

from entities.okta_entities.users.user_models import User
from entities.okta_entities.users.views.user_base_viewset import BaseUserViewSet
from entities.okta_entities.users.user_serializers import UserSerializer

logger = logging.getLogger(__name__)

class UserViewSet(BaseUserViewSet):
    okta_endpoint = "/api/v1/users"
    entity_type = "okta_user"
    serializer_class = UserSerializer
    model = User

    def extract_data(self, okta_data):
        logger.info("Extracting data from Okta response")
        formatted_data = []

        for record in okta_data:
            profile = record.get("profile", {})

            formatted_record = {
                "user_id": record.get("id"),
                "first_name": profile.get("firstName", ""),
                "last_name": profile.get("lastName", ""),
                "mobile_phone": profile.get("mobilePhone", ""),
                "second_email": profile.get("secondEmail", ""),
                "login": profile.get("login", ""),
                "email": profile.get("email", ""),
                "city": profile.get("city", ""),
                "cost_center": profile.get("costCenter", ""),
                "country_code": profile.get("countryCode", ""),
                "custom_profile_properties": profile.get("customProfileProperties", {}),
                "custom_profile_properties_to_ignore": profile.get("customProfilePropertiesToIgnore", []),
                "department": profile.get("department", ""),
                "display_name": profile.get("displayName", ""),
                "division": profile.get("division", ""),
                "employee_number": profile.get("employeeNumber", ""),
                "expire_password_on_create": record.get("expirePasswordOnCreate", None),
                "honorofix_prefix": profile.get("honorofixPrefix", ""),
                "honorofix_suffix": profile.get("honorofixSuffix", ""),
                "locale": profile.get("locale", ""),
                "manager": profile.get("manager", ""),
                "manager_id": profile.get("managerId", ""),
                "middle_name": profile.get("middleName", ""),
                "nick_name": profile.get("nickname", ""),
                "old_password": record.get("oldPassword", ""),
                "organization": profile.get("organization", ""),
                "password": record.get("password", ""),
                "password_inline_hook": record.get("passwordInlineHook", ""),
                "password_hash": record.get("passwordHash", []),
                "postal_address": profile.get("postalAddress", ""),
                "preferred_language": profile.get("preferredLanguage", ""),
                "primary_phone": profile.get("primaryPhone", ""),
                "profile_url": profile.get("profileUrl", ""),
                "recovery_answer": record.get("recoveryAnswer", ""),
                "recovery_question": record.get("recoveryQuestion", ""),
                "state": profile.get("state", ""),
                "status": record.get("status", ""),
                "street_address": profile.get("streetAddress", ""),
                "timezone": profile.get("timezone", ""),
                "title": profile.get("title", ""),
                "user_type": profile.get("userType", ""),
                "zip_code": profile.get("zipCode", ""),
                "realm_id": record.get("realmId", ""),
            }
            formatted_data.append(formatted_record)

        logger.info("Extracted and formatted %d user records from Okta", len(formatted_data))
        return formatted_data