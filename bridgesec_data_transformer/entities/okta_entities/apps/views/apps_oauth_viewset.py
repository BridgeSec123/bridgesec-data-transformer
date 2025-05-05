import logging

from entities.okta_entities.apps.views.apps_base_viewset import BaseAppViewSet
from entities.okta_entities.apps.apps_models import (
    AppOauth,
)
from entities.okta_entities.apps.apps_serializers import (
   AppOauthSerializer,
)

logger = logging.getLogger(__name__)

class AppOauthViewSet(BaseAppViewSet):
    entity_type = "okta_app_oauth"
    serializer_class =  AppOauthSerializer
    model = AppOauth
    
    def extract_data(self, okta_data):
        logger.info("Extracting data from Okta response")
        extracted_data = super().extract_data(okta_data)

        formatted_data = []
        
        for record in extracted_data:
            if record.get("signOnMode") == "OPENID_CONNECT":
                accessibility = record.get("accessibility", {})
                visibility = record.get("visibility", {})
                settings = record.get("settings", {})
                notes = settings.get("notes", {})
                link = record.get("_links", {})
                credentials = record.get("credentials", {})
                oauthClient = credentials.get("oauthClient", {})
                hide = visibility.get("hide", {})
                idp_initiated_login = oauthClient.get("idp_initiated_login", {})
                userNameTemplate = record.get("credentials", {}).get("userNameTemplate", {})
                formatted_record = {
                    "label": record.get("label", ""),
                    "type": (oauthClient.get("application_type") or "service"),
                    "accessibility_error_redirect_url": accessibility.get("errorRedirectUrl", ""),
                    "accessibility_login_redirect_url": accessibility.get("loginRedirectUrl", ""),
                    "accessibility_self_service": accessibility.get("selfService", ""),
                    "admin_note": notes.get("admin", ""),
                    "app_links_json": any(visibility.get("appLinks",{}).values()),
                    "app_settings_json": settings.get("app", ""),
                    "authentication_policy": link.get("policies", ""),
                    "auto_key_rotation": oauthClient.get("autoKeyRotation", False),
                    "auto_submit_toolbar": oauthClient.get("autoSubmitToolbar", False),
                    "client_basic_secret": oauthClient.get("token_endpoint_auth_method", ""),
                    "client_id": oauthClient.get("client_id", ""),
                    "client_uri": oauthClient.get("client_uri", ""),
                    "consent_method": oauthClient.get("consent_method", ""),
                    "enduser_note": notes.get("enduser", ""),
                    "grant_types": oauthClient.get("grant_types", ""),
                    "groups_claim": link.get("groups", ""),
                    "hide_ios": hide.get("iOS", ""),
                    "hide_web": hide.get("web", ""),
                    "implicit_assignment": settings.get("implicitAssignment", ""),
                    "issuer_mode": oauthClient.get("issuer_mode", ""),
                    "jwks": oauthClient.get("jwks", {}),
                    "jwks_uri": oauthClient.get("jwks_uri", ""),
                    "login_mode": idp_initiated_login.get("mode", ""),
                    "login_scopes": idp_initiated_login.get("default_scope", ""),
                    "login_uri": idp_initiated_login.get("login_uri", ""),
                    "logo": record.get("logo", ""),
                    "logo_uri": oauthClient.get("logo_uri", ""),
                    "omit_secret": record.get("omitSecret", ""),
                    "pkce_required": record.get("pkce_required", ""), 
                    "policy_uri": link.get("accessPolicy", ""),
                    "post_logout_redirect_uris": oauthClient.get("post_logout_redirect_uris", ""),
                    "profile": link.get("profileEnrollment", ""),
                    "redirect_uris": oauthClient.get("redirect_uris", ""),
                    "refresh_token_leeway": record.get("refreshTokenLeeway", ""),
                    "refresh_token_rotation": record.get("refreshTokenRotation", ""),
                    "response_types": oauthClient.get("response_types",  ""),
                    "status": record.get("status", ""),
                    "timeouts": record.get("timeouts", ""),
                    "token_endpoint_auth_method": oauthClient.get("token_endpoint_auth_method", ""),
                    "tos_uri": record.get("tos_uri", ""),
                    "user_name_template": userNameTemplate.get("template", ""),
                    "user_name_template_push_status": record.get("credentials", {}),
                    "user_name_template_suffix": record.get("credentials", {}),
                    "user_name_template_type": userNameTemplate.get("type", ""),
                    "wildcard_redirect": oauthClient.get("wildcard_redirect", ""),
                }
                formatted_data.append(formatted_record)
        logger.info("Extracted and formatted %d Identity Provider records from Okta", len(formatted_data))
        
        return formatted_data