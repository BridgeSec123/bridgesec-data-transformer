import logging

from entities.okta_entities.apps.apps_models import (
    AppBookMark,
)
from entities.okta_entities.apps.apps_serializers import (
    AppBookMarkSerializer,
)
from entities.okta_entities.apps.views.apps_base_viewset import BaseAppViewSet

logger = logging.getLogger(__name__)

class AppBookmarkViewSet(BaseAppViewSet):
    entity_type = "okta_app_bookmark"
    serializer_class = AppBookMarkSerializer
    model = AppBookMark
    
    def extract_data(self, okta_data):
        logger.info("Extracting data from Okta response")
        extracted_data = super().extract_data(okta_data)

        formatted_data = []
        
        for record in extracted_data:
            if record.get("signOnMode") == "BOOKMARK":
                accessibility = record.get("accessibility", {})
                visibility = record.get("visibility", {})
                settings = record.get("settings", {})
                note = settings.get("notes", {})
                hide = visibility.get("hide", {})

                formatted_record = {
                    "label": record.get("label", ""),
                    "url": settings.get("app", {}).get("url", ""),
                    "accessibility_error_redirect_url": accessibility.get("errorRedirectUrl", ""),
                    "accessibility_login_redirect_url": accessibility.get("loginRedirectUrl", ""),
                    "accessibility_self_service": accessibility.get("selfService", ""),
                    "admin_note": note.get("admin", ""),
                    "app_links_json":  any(visibility.get("appLinks",{}).values()),
                    "authentication_policy": record.get("authentication_policy", ""),
                    "auto_submit_toolbar": visibility.get("autoSubmitToolbar", ""),
                    "enduser_note": note.get("enduser", ""),
                    "hide_ios": hide.get("iOS", ""),
                    "hide_web": hide.get("web", ""),
                    "logo" : record.get("logo", ""),
                    "request_integration": settings.get("app", {}).get("requestIntegration", True),
                    "timeouts": record.get("timeouts", ""),
                    "status": record.get("status", "")
                }
                formatted_data.append(formatted_record)
        logger.info("Extracted and formatted %d Identity Provider records from Okta", len(formatted_data))
        
        return formatted_data