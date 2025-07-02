import logging

from entities.okta_entities.apps.apps_models import AppOauth
from entities.okta_entities.apps.apps_serializers import AppOauthSerializer
from entities.okta_entities.apps.views.apps_base_viewset import BaseAppViewSet

logger = logging.getLogger(__name__)

class AppOauthViewSet(BaseAppViewSet):
    entity_type = "okta_app_oauth"
    serializer_class = AppOauthSerializer
    model = AppOauth

    def extract_data(self, okta_data):
        logger.info("Extracting data from Okta response")
        extracted_data = super().extract_data(okta_data)

        formatted_data = []

        for record in extracted_data:
            if not isinstance(record, dict):
                logger.error(f"Invalid record (not a dict): {record}")
                continue

            if record.get("signOnMode") == "OPENID_CONNECT":
                accessibility = record.get("accessibility", {})
                visibility = record.get("visibility", {})
                hide = visibility.get("hide", {})
                credentials = record.get("credentials", {})
                userNameTemplate = credentials.get("userNameTemplate", {})
                settings = record.get("settings", {})
                note = settings.get("notes", {})
                oauthclient = settings.get("oauthClient", {})
                link = record.get("_links", {})

                formatted_record = {
                    "app_id": record.get("id", ""),
                    "label": record.get("label", ""),
                    "type": oauthclient.get("application_type","service"),
                    "accessibility_error_redirect_url": accessibility.get("errorRedirectUrl", ""),
                    "accessibility_login_redirect_url": accessibility.get("loginRedirectUrl", ""),
                    "accessibility_self_service": accessibility.get("selfService", ""),
                    "admin_note": note.get("admin", ""),
                    "app_links_json": any(visibility.get("appLinks", {}).values()),
                    "app_settings_json": record.get("app", "{}"),
                    "authentication_policy": record.get("authentication_policy", ""),
                    "auto_key_rotation": credentials.get("oauthClient", {}).get("autoKeyRotation", ""),
                    "auto_submit_toolbar": visibility.get("autoSubmitToolbar", ""),
                    "client_basic_secret": record.get("client_basic_secret", ""),
                    "client_id": credentials.get("oauthClient", {}).get("client_id", ""),
                    "client_uri": oauthclient.get("client_uri", ""),
                    "consent_method": oauthclient.get("consent_method", ""),
                    "enduser_note": note.get("enduser", ""),
                    "grant_types": oauthclient.get("grant_types", ""),
                    "groups_claim": record.get("group_claims", []),
                    "hide_ios": hide.get("iOS", False),
                    "hide_web": hide.get("web", False),
                    "implicit_assignment": settings.get("implicitAssignment", ""),
                    "issuer_mode": record.get("issuer_mode", ""),
                    "jwks": record.get("jwks", {}),
                    "jwks_uri": record.get("jwks_uri", ""),
                    "login_mode": oauthclient.get("idp_initiated_login", {}).get("mode", ""),
                    "login_scopes": oauthclient.get("idp_initiated_login", {}).get("default_scope", ""),
                    "login_uri": record.get("login_uri", ""),
                    "logo": link.get("logo", [{}])[0].get("href", ""),
                    "logo_uri": record.get("logo_uri", ""),
                    "omit_secret": record.get("omit_secret", ""),
                    "pkce_required": credentials.get("oauthClient", {}).get("pkce_required", ""),
                    "policy_uri": record.get("policy_uri", ""),
                    "post_logout_redirect_uris": oauthclient.get("post_logout_redirect_uris", ""),
                    "profile": record.get("profile", "{}"),
                    "redirect_uris": oauthclient.get("redirect_uris", ""),
                    "refresh_token_leeway": record.get("refresh_token_leeway", 2),
                    "refresh_token_rotation": record.get("refresh_token_rotation", ""),
                    "response_types": oauthclient.get("response_types", ""),
                    "status": record.get("status", ""),
                    "timeouts": record.get("timeouts", []),
                    "token_endpoint_auth_method": credentials.get("oauthClient", {}).get("token_endpoint_auth_method", ""),
                    "tos_uri": record.get("tos_uri", ""),
                    "user_name_template": userNameTemplate.get("template", ""),
                    "user_name_template_push_status": record.get("user_name_template_push_status", ""),
                    "user_name_template_suffix": record.get("user_name_template_suffix", ""),
                    "user_name_template_type": userNameTemplate.get("type", ""),
                    "wildcard_redirect": oauthclient.get("wildcard_redirect", ""),
                }
                formatted_data.append(formatted_record)

        logger.info("Extracted and formatted %d app oauth records from Okta", len(formatted_data))
        return formatted_data

