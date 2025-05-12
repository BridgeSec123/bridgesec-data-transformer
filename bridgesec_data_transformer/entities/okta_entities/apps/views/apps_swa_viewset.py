import logging

from entities.okta_entities.apps.views.apps_base_viewset import  BaseAppViewSet
from entities.okta_entities.apps.apps_models import (
    AppSwa,
)
from entities.okta_entities.apps.apps_serializers import (
    AppSwaSerializer,
)

logger = logging.getLogger(__name__)

class AppSwaViewSet(BaseAppViewSet):
    entity_type = "okta_app_swa"
    serializer_class =  AppSwaSerializer
    model = AppSwa

    def extract_data(self, okta_data):
        logger.info("Extracting data from Okta response")
        extracted_data = super().extract_data(okta_data)

        formatted_data = []
        
        for record in extracted_data:
            if record.get("signOnMode") == "AUTO_LOGIN":
                accessibility = record.get("accessibility", {})
                visibility = record.get("visibility", {})
                signon = record.get("settings", {}).get("signOn", {})
                hide = visibility.get("hide", {})
                logo_list = record.get("_links", {}).get("logo", [{}])
                logo = logo_list[0].get("href", "") if logo_list and isinstance(logo_list, list) else ""
                user_template = record.get("credentials", {}).get("userNameTemplate", {})

                # Format the record
                formatted_record = {
                    "label": record.get("label", ""),
                    "accessibility_error_redirect_url": accessibility.get("errorRedirectUrl", ""),
                    "accessibility_login_redirect_url": accessibility.get("loginRedirectUrl", ""),
                    "accessibility_self_service": accessibility.get("selfService", ""),
                    "admin_note": record.get("adminNote", ""),
                    "app_links_json": bool(visibility.get("appLinks", {})),
                    "auto_submit_toolbar": visibility.get("autoSubmitToolbar", ""),
                    "button_field": record.get("buttonField", ""),
                    "checkbox": record.get("checkbox", ""),
                    "enduser_note": record.get("enduserNote", ""),
                    "hide_ios": hide.get("iOS", ""),
                    "hide_web": hide.get("web", ""),
                    "logo": logo,
                    "password_field": record.get("passwordField", ""),
                    "preconfigured_app": record.get("preconfiguredApp", ""),
                    "redirect_url": signon.get("redirectUrl", ""),
                    "status": record.get("status", ""),
                    "timeouts": record.get("timeouts", ""),
                    "url": record.get("url", ""),
                    "url_regex": record.get("urlRegex", ""),
                    "user_name_template": user_template.get("template", ""),
                    "user_name_template_push_status": record.get("userNameTemplatePushStatus", ""),
                    "user_name_template_suffix": record.get("userNameTemplateSuffix", ""),
                    "user_name_template_type": user_template.get("type", ""),
                    "username_field": record.get("usernameField", ""),
                }
                
                # Add the formatted record to the list
                formatted_data.append(formatted_record)

            logger.info("Extracted and formatted %d Identity Provider records from Okta", len(formatted_data))
        
        return formatted_data
