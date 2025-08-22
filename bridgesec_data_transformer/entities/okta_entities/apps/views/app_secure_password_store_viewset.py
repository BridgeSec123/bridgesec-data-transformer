import logging

from entities.okta_entities.apps.apps_models import (
    AppSecurePasswordStore,
)
from entities.okta_entities.apps.apps_serializers import (
    AppSecurePasswordStoreSerializer,
)
from entities.okta_entities.apps.views.apps_base_viewset import BaseAppViewSet

logger = logging.getLogger(__name__)

class AppSecurePasswordStoreViewSet(BaseAppViewSet):
    entity_type = "okta_app_secure_password_store"
    serializer_class =  AppSecurePasswordStoreSerializer
    model = AppSecurePasswordStore
    
    def extract_data(self, okta_data):
        logger.info("Extracting data from Okta response")
        extracted_data = super().extract_data(okta_data)

        formatted_data = []
        
        for record in extracted_data:
            if record.get("signOnMode") == "SECURE_PASSWORD_STORE":
                accessibility = record.get("accessibility", {})
                visibility = record.get("visibility", {})
                settings = record.get("settings", {})
                notes = settings.get("notes", {})
                app = settings.get("app", {})
                credentials = record.get("credentials", {})
                hide = visibility.get("hide", {})
                userNameTemplate = credentials.get("userNameTemplate", {})
            
                formatted_record = {
                    "label": record.get("label", ""),
                    "username_field" : app.get("usernameField", ""),
                    "password_field": app.get("passwordField", ""),
                    "url": app.get("url", ""),
                    "accessibility_error_redirect_url": accessibility.get("errorRedirectUrl", ""),
                    "accessibility_login_redirect_url": accessibility.get("loginRedirectUrl", ""),
                    "accessibility_self_service": accessibility.get("selfService", False),
                    "admin_note": notes.get("admin", ""),
                    "app_links_json": record.get("appLinks", "{}"), 
                    "auto_submit_toolbar": visibility.get("autoSubmitToolbar", False),
                    "credentials_scheme": credentials.get("scheme", ""),
                    "enduser_note": notes.get("enduser", ""),
                    "hide_ios": hide.get("iOS", False),
                    "hide_web": hide.get("web", False),
                    "logo": record.get("logo", ""),
                    "optional_field1" : app.get("optionalField1", ""),
                    "optional_field1_value" : app.get("optionalField1Value", ""),
                    "optional_field2" : app.get("optionalField2", ""),
                    "optional_field2_value" : app.get("optionalField2Value", ""),
                    "optional_field3" : app.get("optionalField3", ""),
                    "optional_field3_value" : app.get("optionalField3Value", ""),
                    "reveal_password" : credentials.get("revealPassword", False),
                    "shared_password" : record.get("shared_password", ""),
                    "shared_username" : record.get("shared_username", ""),
                    "status": record.get("status", ""),
                    "timeouts": record.get("timeouts", []),
                    "user_name_template": userNameTemplate.get("template", ""),
                    "user_name_template_push_status": record.get("user_name_template_push_status", ""),
                    "user_name_template_suffix": record.get("user_name_template_suffix", ""),
                    "user_name_template_type": userNameTemplate.get("type", "")
                }

                formatted_data.append(formatted_record)
        logger.info("Extracted and formatted %d apps oauth records from Okta", len(formatted_data))

        return formatted_data