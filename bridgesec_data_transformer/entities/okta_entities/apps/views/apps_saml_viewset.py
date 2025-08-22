import logging

from entities.okta_entities.apps.apps_models import (
    AppSAML,
)
from entities.okta_entities.apps.apps_serializers import (
    AppSAMLSerializer,
)
from entities.okta_entities.apps.views.apps_base_viewset import BaseAppViewSet

logger = logging.getLogger(__name__)

class AppSAMLViewSet(BaseAppViewSet):
    entity_type = "okta_app_saml"
    serializer_class =  AppSAMLSerializer
    model = AppSAML
    
    def extract_data(self, okta_data):
        logger.info("Extracting data from Okta response")
        extracted_data = super().extract_data(okta_data)

        formatted_data = []
        
        for record in extracted_data:
            if record.get("signOnMode") == "SAML_2_0":
                accessibility = record.get("accessibility", {})
                visibility = record.get("visibility", {})
                settings = record.get("settings", {})
                note = settings.get("notes", {})
                signon = settings.get("signOn", {})
                hide = visibility.get("hide", {})
                userNameTemplate=record.get("credentials", {}).get("userNameTemplate", {})
                
                raw_statements = signon.get("attributeStatements", [])
                attribute_statements = []

                for s in raw_statements:
                    # normalize only if actual keys exist
                    attribute_statements.append({
                        "filter_type": s.get("filterType"),
                        "filter_value": s.get("filterValue")
                    })

                formatted_record = {
                    "label": record.get("label", ""),
                    "accessibility_error_redirect_url": accessibility.get("errorRedirectUrl", ""),
                    "accessibility_login_redirect_url": accessibility.get("loginRedirectUrl", ""),
                    "accessibility_self_service": accessibility.get("selfService", False),
                    "acs_endpoints": signon.get("acsEndpoints", []),
                    "admin_note": note.get("admin", ""),
                    "app_links_json":  any(visibility.get("appLinks",{}).values()),
                    "app_settings_json": any(visibility.get("appLinks", {}).values()),
                    "attribute_statements": attribute_statements,
                    "audience": signon.get("audience", ""),
                    "authentication_policy": record.get("authentication_policy", ""),
                    "authn_context_class_ref": signon.get("authnContextClassRef", ""),
                    "auto_submit_toolbar": visibility.get("autoSubmitToolbar", ""),
                    "default_relay_state": signon.get("defaultRelayState", ""),
                    "destination": signon.get("destination", ""),
                    "digest_algorithm": signon.get("digestAlgorithm", ""),
                    "enduser_note": note.get("enduser", ""),
                    "hide_ios": hide.get("iOS", ""),
                    "hide_web": hide.get("web", ""),
                    "honor_force_authn": signon.get("honorForceAuthn", False),
                    "idp_issuer": signon.get("idpIssuer", ""),
                    "inline_hook_id": signon.get("inlineHooks", ""),
                    "implicit_assignment" : settings.get("implicitAssignment", ""),
                    "key_name": record.get("keyName", ""),
                    "key_years_valid": record.get("keyYearsValid", 2),
                    "logo" : record.get("logo", ""),
                    "preconfigured_app": record.get("preconfiguredApp", ""),
                    "recipient": signon.get("recipient", ""),
                    "request_compressed": signon.get("requestCompressed", ""),
                    "response_signed": signon.get("responseSigned", ""),
                    "saml_signed_request_enabled": signon.get("samlSignedRequest", ""),
                    "saml_version": record.get("samlVersion", "2.0"),
                    "signature_algorithm": signon.get("signatureAlgorithm", ""),
                    "single_logout_certificate": record.get("singleLogoutCertificate", ""),
                    "single_logout_issuer": record.get("singleLogoutIssuer", ""),
                    "single_logout_url": record.get("singleLogoutUrl", ""),
                    "sp_issuer": signon.get("spIssuer", ""),
                    "sso_url": signon.get("ssoAcsUrl", ""),
                    "status": record.get("status", ""),
                    "subject_name_id_format": signon.get("subjectNameIdFormat", ""),
                    "subject_name_id_template": signon.get("subjectNameIdTemplate", ""),
                    "timeouts": record.get("timeouts", []),
                    "user_name_template": userNameTemplate.get("template", "${source.login}"),
                    "user_name_template_push_status": record.get("userNameTemplatePushStatus", ""),
                    "user_name_template_suffix": record.get("userNameTemplateSuffix", ""),
                    "user_name_template_type": userNameTemplate.get("type", "BUILT_IN"),
                    "acs_endpoints_indices": record.get("acs_endpoints_indices", {})
                }
                formatted_data.append(formatted_record)
        logger.info("Extracted and formatted %d app saml records from Okta", len(formatted_data))
        
        return formatted_data