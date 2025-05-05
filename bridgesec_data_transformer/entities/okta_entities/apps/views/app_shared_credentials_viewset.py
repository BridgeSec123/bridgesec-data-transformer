import logging

from entities.okta_entities.apps.views.apps_base_viewset import BaseAppViewSet
from entities.okta_entities.apps.apps_models import (
     AppSharedCredentials,
)
from entities.okta_entities.apps.apps_serializers import (
    AppSharedCredentialsSerializer,
)

logger = logging.getLogger(__name__)

class AppSharedCredentialsViewSet(BaseAppViewSet):
    entity_type = "okta_app_shared_credentials"
    serializer_class =  AppSharedCredentialsSerializer
    model =  AppSharedCredentials
    
    def extract_data(self, okta_data):
        logger.info("Extracting data from Okta response")
        extracted_data = super().extract_data(okta_data)

        formatted_data = []
        
        for record in extracted_data:
            
                accessibility = record.get("accessibility", {})
                visibility = record.get("visibility", {})
                settings = record.get("settings", {})
                notes = settings.get("notes", {})
                oauthClient = settings.get("oauthClient", {})
                hide = visibility.get("hide", {})
                userNameTemplate = record.get("credentials", {}).get("userNameTemplate", {})

                formatted_record = {
                                "label": record.get("label", ""),
                                "accessibility_error_redirect_url": accessibility.get("errorRedirectUrl", ""),
                                "accessibility_login_redirect_url": accessibility.get("loginRedirectUrl", ""),
                                "accessibility_self_service": accessibility.get("selfService", ""),
                                "admin_note": notes.get("admin", ""),
                                "app_links_json": any(visibility.get("appLinks",{}).values()),
                                "auto_submit_toolbar": oauthClient.get("autoSubmitToolbar", False),
                                "button_field": record.get("buttonField", ""),
                                "checkbox": record.get("checkbox", ""),
                                "enduser_note": notes.get("enduser", ""),
                                "hide_ios": hide.get("iOS", ""),
                                "hide_web": hide.get("web", ""),
                                "logo": record.get("logo", ""),
                                "password_field": record.get("passwordField", ""),
                                "preconfigured_app": record.get("preconfiguredApp", ""),
                                "redirect_url": record.get("redirectUrl", ""),
                                "shared_password": record.get("sharedPassword", ""),
                                "shared_username": record.get("sharedUsername", ""),
                                "status": record.get("status", ""),
                                "timeouts": record.get("timeouts", ""),
                                "url": record.get("url", ""),
                                "url_regex": record.get("urlRegex", ""),
                                "user_name_template": userNameTemplate.get("template", ""),
                                "user_name_template_push_status": record.get("credentials", {}),
                                "user_name_template_suffix": record.get("credentials", {}),
                                "user_name_template_type": userNameTemplate.get("type", ""),
                                "username_field": record.get("usernameField", ""),
                            }
                formatted_data.append(formatted_record)
        logger.info("Extracted and formatted %d App Shared Credentials records from Okta", len(formatted_data))
        
        return formatted_data