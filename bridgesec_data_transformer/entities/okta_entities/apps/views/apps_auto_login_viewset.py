import logging

from entities.okta_entities.apps.apps_models import AppAutoLogin
from entities.okta_entities.apps.apps_serializers import AppAutoLoginSerializer
from entities.okta_entities.apps.views.apps_base_viewset import BaseAppViewSet

logger = logging.getLogger(__name__)

class AppAutoLoginViewSet(BaseAppViewSet):
    entity_type = "okta_app_auto_login"
    serializer_class =  AppAutoLoginSerializer
    model = AppAutoLogin

    def extract_data(self, okta_data):
        logger.info("Extracting data from Okta response")
        extracted_data = super().extract_data(okta_data)

        formatted_data = []
        for record in extracted_data:
            if record.get("signOnMode") == "AUTO_LOGIN":
                accessibility = record.get("accessibility", {})
                credentials = record.get("credentials", {})
                visibility = record.get("visibility", {})
                signon = record.get("settings", {}).get("signOn", {})
                settings = record.get("settings", {})
                hide = visibility.get("hide", {})
                logo_list = record.get("_links", {}).get("logo", [{}])
                logo = logo_list[0].get("href", "") if logo_list and isinstance(logo_list, list) else ""
                username_template = credentials.get("userNameTemplate", {})

                # Format the record
                formatted_record = {
                    "label": record.get("label", ""),
                    "accessibility_error_redirect_url": accessibility.get("errorRedirectUrl", ""),
                    "accessibility_login_redirect_url": accessibility.get("loginRedirectUrl", ""),
                    "accessibility_self_service": accessibility.get("selfService", ""),
                    "admin_note": record.get("adminNote", ""),
                    "app_links_json": any(visibility.get("appLinks",{}).values()),
                    "app_settings_json": settings.get("app", "{}"),
                    "auto_submit_toolbar": visibility.get("autoSubmitToolbar", ""),
                    "credentials_scheme": credentials.get("scheme", ""),
                    "enduser_note": record.get("enduserNote", ""),
                    "hide_ios": hide.get("iOS", ""),
                    "hide_web": hide.get("web", ""),
                    "logo": logo,
                    "preconfigured_app": record.get("preconfiguredApp", ""),
                    "reveal_password": credentials.get("revealPassword", False),
                    "shared_password": record.get("sharedPassword", ""),
                    "shared_username": record.get("sharedUsername", ""),
                    "sign_on_redirect_url": signon.get("redirectUrl", ""),
                    "sign_on_url": signon.get("loginUrl", ""),
                    "status": record.get("status", ""),
                    "timeouts": record.get("timeouts", []),
                    "user_name_template": username_template.get("template", ""),
                    "user_name_template_push_status": record.get("userNameTemplatePushStatus", ""),
                    "user_name_template_suffix": record.get("userNameTemplateSuffix", ""),
                    "user_name_template_type": username_template.get("type", "")
                }

                # Add the formatted record to the list
                formatted_data.append(formatted_record)

        logger.info("Extracted and formatted %d app auto login records from Okta", len(formatted_data))

        return formatted_data
