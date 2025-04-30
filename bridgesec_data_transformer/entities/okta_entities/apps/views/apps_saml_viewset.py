import logging

from rest_framework import status
from rest_framework.response import Response

from entities.okta_entities.apps.views.apps_base_viewset import  BaseAppViewSet
from entities.okta_entities.apps.apps_models import (
    AppSAML,
)
from entities.okta_entities.apps.apps_serializers import (
   AppSAMLSerializer,
)

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

                formatted_record = {
                    "label": record.get("label", ""),
                    "accessibility_error_redirect_url": accessibility.get("errorRedirectUrl", ""),
                    "accessibility_login_redirect_url": accessibility.get("loginRedirectUrl", ""),
                    "accessibility_self_service": accessibility.get("selfService", ""),
                    "acs_endpoints": signon.get("acsEndpoints",{}),
                    "admin_note": note.get("admin", ""),
                    "app_links_json": visibility.get("appLinks", ""),
                    "app_settings_json": any(visibility.get("appLinks",{}).values()),
                    "attribute_statements": record.get("attributeStatements", {}),
                    "audience": signon.get("audienceOverride", ""),
                    "authentication_policy": record.get("authentication_policy", ""),
                    "authn_context_class_ref": signon.get("authnContextClassRef", ""),
                    "auto_submit_toolbar": visibility.get("autoSubmitToolbar", ""),
                    "default_relay_state": signon.get("defaultRelayState", ""),
                    "destination": signon.get("destination", ""),
                    "digest_algorithm": signon.get("digestAlgorithm", ""),
                    "enduser_note": note.get("enduser", ""),
                    "hide_ios": hide.get("iOS", ""),
                    "hide_web": hide.get("web", ""),
                    "honor_force_authn": signon.get("honorForceAuthn", ""),
                    "idp_issuer": signon.get("idpIssuer", ""),
                    "inline_hook_id": signon.get("inlineHooks", ""),
                    "implicit_assignment" : settings.get("implicitAssignment", ""),
                    "key_name": record.get("keyName", ""),
                    "key_years_valid": record.get("keyYearsValid", ""),
                    "logo" : record.get("logo", ""),
                    "preconfigured_app": record.get("preconfiguredApp", ""),
                    "recipient": signon.get("recipient", ""),
                    "request_compressed": signon.get("requestCompressed", ""),
                    "response_signed": signon.get("responseSigned", ""),
                    "saml_signed_request_enabled": signon.get("samlSignedRequest", ""),
                    "saml_version": record.get("samlVersion", ""),
                    "signature_algorithm": signon.get("signatureAlgorithm", ""),
                    "single_logout_certificate": record.get("singleLogoutCertificate", ""),
                    "single_logout_issuer": record.get("singleLogoutIssuer", ""),
                    "single_logout_url": record.get("singleLogoutUrl", ""),
                    "sp_issuer": signon.get("spIssuer", ""),
                    "sso_url": signon.get("ssoAcsUrl", ""),
                    "status": record.get("status", ""),
                    "subject_name_id_format": signon.get("subjectNameIdFormat", ""),
                    "subject_name_id_template": signon.get("subjectNameIdTemplate", ""),
                    "timeouts": record.get("timeouts", ""),
                    "user_name_template": userNameTemplate.get("template", ""),
                    "user_name_template_push_status": record.get("userNameTemplatePushStatus", ""),
                    "user_name_template_suffix": record.get("userNameTemplateSuffix", ""),
                    "user_name_template_type": userNameTemplate.get("type", ""),
                    "acs_endpoints_indices": record.get("acs_endpoints_indices",{})
                }
                formatted_data.append(formatted_record)
        logger.info("Extracted and formatted %d Identity Provider records from Okta", len(formatted_data))
        
        return formatted_data