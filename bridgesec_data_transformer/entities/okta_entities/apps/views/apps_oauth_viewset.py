import logging

from entities.entity_filters import should_skip_app_extraction
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
                # Check if this app label should be excluded
                app_label = record.get("label", "")
                if should_skip_app_extraction(app_label):
                    logger.info(f"Skipping app extraction for label: {app_label}")
                    continue

                # Extract client_id early to check if this is a system app
                credentials = record.get("credentials", {})
                oauthClient = credentials.get("oauthClient", {})
                client_id = oauthClient.get("client_id", "")

                # Skip system-level apps that don't have a client_id
                # System apps (like "Okta End User Settings") have empty client_id
                if not client_id or client_id.strip() == "":
                    logger.info(f"Skipping system app without client_id: {app_label}")
                    continue

                accessibility = record.get("accessibility", {})
                visibility = record.get("visibility", {})
                hide = visibility.get("hide", {})
                userNameTemplate = credentials.get("userNameTemplate", {})
                settings = record.get("settings", {})
                notes = settings.get("notes", {})
                oauthClient_settings = settings.get("oauthClient", {})
                link = record.get("_links", {})
                authentication_policy = link.get("accessPolicy", {}).get("href", "").rstrip("/").split("/")[-1]
                idp_initiated_login = oauthClient_settings.get("idp_initiated_login", {})
                refresh_token = oauthClient_settings.get("refresh_token", {})

                type = oauthClient_settings.get("application_type") or "service"

                jwks_formatted = []
                if oauthClient.get("token_endpoint_auth_method") == "private_key_jwt":
                    jwks_data = oauthClient_settings.get("jwks", {}).get("keys", [])
                    for key in jwks_data:
                        jwks_entry = {
                            "kty": key.get("kty"),
                            "kid": key.get("kid")
                        }
                        if key.get("kty") == "RSA":
                            jwks_entry["e"] = key.get("e")
                            jwks_entry["n"] = key.get("n")
                        elif key.get("kty") == "EC":
                            jwks_entry["x"] = key.get("x")
                            jwks_entry["y"] = key.get("y")
                        jwks_formatted.append(jwks_entry)

                                
                formatted_record = {
                    "app_id": record.get("id", ""),
                    "label": record.get("label", ""),
                    "type": type,
                    "accessibility_error_redirect_url": accessibility.get("errorRedirectUrl", ""),
                    "accessibility_login_redirect_url": accessibility.get("loginRedirectUrl", ""),
                    "accessibility_self_service": accessibility.get("selfService", False),
                    "admin_note": notes.get("admin", ""),
                    "app_links_json": any(visibility.get("appLinks",{}).values()),  
                    "app_settings_json": settings.get("apps", "{}"),
                    "authentication_policy": authentication_policy,
                    "auto_key_rotation": oauthClient.get("autoKeyRotation", False),
                    "auto_submit_toolbar": visibility.get("autoSubmitToolbar", False),
                    "client_basic_secret": record.get("client_basic_secret", ""),
                    "client_id": client_id,  # Already extracted and validated above
                    "client_uri": oauthClient_settings.get("client_uri", ""),
                    "consent_method": oauthClient_settings.get("consent_method", ""),
                    "enduser_note": notes.get("enduser", ""),
                    "grant_types": oauthClient_settings.get("grant_types", []) or [],
                    "groups_claim": link.get("groups", []) if isinstance(link.get("groups", []), list) else [],
                    "hide_ios": hide.get("iOS", False),
                    "hide_web": hide.get("web", False),
                    "implicit_assignment": settings.get("implicitAssignment", False),
                    "issuer_mode": oauthClient_settings.get("issuer_mode", ""),
                    "jwks": jwks_formatted,
                    "jwks_uri": oauthClient.get("jwks_uri", ""),
                    "login_mode": idp_initiated_login.get("mode", ""),
                    "login_scopes": idp_initiated_login.get("default scope", []) or [],
                    "login_uri": record.get("login_uri", ""),
                    "logo": record.get("logo"),
                    "logo_uri": oauthClient_settings.get("logo_uri", ""),
                    "omit_secret": record.get("omitSecret", False),
                    "pkce_required": oauthClient.get("pkce_required", False),
                    "policy_uri": link.get("policies", {}).get("hef", ""),
                    "post_logout_redirect_uris": oauthClient_settings.get("post_logout_redirect_uris", []) or [],
                    "profile": record.get("profile", "{}"),
                    "redirect_uris": oauthClient_settings.get("redirect_uris", []) or [],
                    "refresh_token_leeway": refresh_token.get("leeway", 0),
                    "refresh_token_rotation": refresh_token.get("rotation_type", ""),
                    "response_types": oauthClient_settings.get("response_types", []) or [],
                    "status": record.get("status", ""),
                    "timeouts": record.get("timeouts", []) if isinstance(record.get("timeouts", []), list) else [],
                    "token_endpoint_auth_method": oauthClient.get("token_endpoint_auth_method", ""),
                    "tos_uri": record.get("tos_uri", ""),
                    "user_name_template": userNameTemplate.get("template", ""),
                    "user_name_template_push_status": record.get("user_name_template_push_status", ""),
                    "user_name_template_suffix": record.get("user_name_template_suffix", ""),
                    "user_name_template_type": userNameTemplate.get("type", ""),
                    "wildcard_redirect": oauthClient_settings.get("wildcard_redirect", ""),
                    "frontchannel_logout_uri": oauthClient_settings.get("frontchannel_logout_uri", ""),
                    "participate_slo": oauthClient_settings.get("participate_slo", False),
                }
                # based on the app type we can set some mandatory fields checks.
                if type == "web":
                    if not formatted_record.get("grant_types"):
                        formatted_record["grant_types"] = ["authorization_code"]
                    if not formatted_record.get("response_types"):
                        formatted_record["response_types"] = ["code"]
                    if not formatted_record.get("redirect_uris"):
                        formatted_record["redirect_uris"] = ["https://example.com/"]

                elif type == "service":
                    if not formatted_record.get("grant_types"):
                        formatted_record["grant_types"] = ["client_credentials"]
                    if not formatted_record.get("response_types"):
                        formatted_record["response_types"] = ["token"]
                    if not formatted_record.get("token_endpoint_auth_method"):
                        formatted_record["token_endpoint_auth_method"] = "private_key_jwt"
                    if not formatted_record.get("jwks"):
                        formatted_record["jwks"] = []
        
                formatted_data.append(formatted_record)
        logger.info("Extracted and formatted %d apps oauth records from Okta", len(formatted_data))
        return formatted_data

