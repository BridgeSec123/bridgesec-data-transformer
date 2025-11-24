from entities.okta_entities.administrators.views import (
    AdminResourceSetViewSet, AdminRoleCustomViewSet, BaseAdministratorViewSet)
from entities.okta_entities.apps.views import (
    AppAccessPolicyAssignmentViewSet, AppAutoLoginViewSet, AppBasicAuthViewSet,
    AppBookmarkViewSet, AppGroupAssignmentsViewSet, AppOauthApiScopeViewSet,
    AppOauthPostRedirectUriViewSet, AppOauthRedirectUriViewSet,
    AppOauthRoleAssignmentViewSet, AppOauthViewSet, AppPolicyRuleSignOnViewSet,
    AppPolicySignOnViewSet, AppSAMLSettingsViewSet, AppSAMLViewSet,
    AppsGroupAssignmentViewSet, AppSharedCredentialsViewSet, AppSwaViewSet,
    AppUserBaseSchemaPropertyViewSet, AppUserSchemaPropertyViewSet,
    AppUserViewSet)
from entities.okta_entities.apps.views.app_secure_password_store_viewset import \
    AppSecurePasswordStoreViewSet
from entities.okta_entities.apps.views.app_three_field_viewset import \
    AppThreeFieldViewSet
from entities.okta_entities.apps.views.apps_access_policy_assignment_viewset import \
    AppAccessPolicyAssignmentViewSet
from entities.okta_entities.apps.views.apps_auto_login_viewset import \
    AppAutoLoginViewSet
from entities.okta_entities.apps.views.apps_base_viewset import BaseAppViewSet
from entities.okta_entities.apps.views.apps_basic_auth_viewset import \
    AppBasicAuthViewSet
from entities.okta_entities.auth_server.views import (
    AuthorizationServerClaimDefaultViewSet, AuthorizationServerClaimViewSet,
    AuthorizationServerDefaultViewSet, AuthorizationServerPolicyRuleViewSet,
    AuthorizationServerPolicyViewSet, AuthorizationServerScopeViewSet,
    AuthorizationServerViewSet, AuthTrustedServerViewSet,
    BaseAuthServerViewSet)
from entities.okta_entities.authenticator.views import (
    AuthenticatorViewSet, BaseAuthenticatorViewSet, OktaFactorViewSet)
from entities.okta_entities.behavior.views import BehaviorViewSet
from entities.okta_entities.brands.views import (BaseBrandViewSet,
                                                 BrandEntityViewSet,
                                                 EmailDomainViewset,
                                                 ThemeViewset)
from entities.okta_entities.campaign.views import CampaignViewSet
from entities.okta_entities.captchas.views import (
    BaseCaptchaViewSet, CaptchaOrgWideSettingsViewSet, CaptchaViewSet)
from entities.okta_entities.catalog.views import (
    BaseCatalogViewSet, CatalogEntryDefaultViewSet,
    CatalogEntryUserAccessRequestFieldsViewSet, EndUserMyRequestsViewSet)
from entities.okta_entities.device_assurance_policies.views import (
    BaseDeviceAssurancePolicyViewSet, DeviceAndroidViewSet, DeviceIOSViewSet,
    DeviceMacOSViewSet, DeviceWindowsViewSet)
from entities.okta_entities.email.views import (BaseEmailViewSet,
                                                EmailSmtpServerViewSet)
from entities.okta_entities.entitlements.views import (
    BaseEntitlementViewSet, EntitlementBundleViewSet, EntitlementViewSet,
    PrincipalEntitlementsViewSet)
from entities.okta_entities.event_hook.views import EventHookViewSet
from entities.okta_entities.groups.views import (BaseGroupViewSet,
                                                 GroupEntityViewSet,
                                                 GroupMembershipViewSet,
                                                 GroupOwnerViewSet,
                                                 GroupRoleViewSet,
                                                 GroupRuleViewSet,
                                                 GroupSchemaPropertyViewSet)
from entities.okta_entities.identity_providers.views import (
    BaseIdentityProviderViewSet, IdentityProviderOIDCViewSet,
    IdentityProviderSAMLViewSet, IdentityProviderSocialViewSet)
from entities.okta_entities.inline_hooks.views import InlineHookEntityViewSet
from entities.okta_entities.link.views import (BaseLinkViewSet,
                                               OktaLinkDefinitionViewSet)
from entities.okta_entities.network_zone.views import NetworkZoneViewSet
from entities.okta_entities.org.views import OrgViewSet
from entities.okta_entities.policies.views import (
    BasePolicyViewSet, PolicyMFAViewSet, PolicyPasswordViewSet,
    PolicyProfileEnrollmentAppsViewSet, PolicyProfileEnrollmentViewSet,
    PolicyRuleIDPDiscoveryViewSet, PolicyRuleMFAViewSet,
    PolicyRulePasswordViewSet, PolicyRuleProfileEnrollmentViewSet,
    PolicyRuleSignOnViewSet, PolicySignOnViewSet)
from entities.okta_entities.rate_limits.views import (
    BaseRateLimitViewSet, PrincipalRateLimitViewSet,
    RateLimitAdminNotificationViewSet, RateLimitWarningThresholdViewSet)
from entities.okta_entities.requests.views import (BaseRequestConditionViewSet,
                                                   RequestConditionViewSet,
                                                   RequestSequenceViewSet,
                                                   RequestSettingsViewSet,
                                                   RequestTypeViewSet)
from entities.okta_entities.sms_templates.views import SmsTemplateViewSet
from entities.okta_entities.threat_insights.views import ThreatInsightViewSet
from entities.okta_entities.trusted_origins.views import TrustedOriginViewSet
from entities.okta_entities.users.views import (AdminRoleTargetsViewSet,
                                                BaseUserViewSet,
                                                RoleSubscriptionViewSet,
                                                UserAdminRolesViewSet,
                                                UserBaseSchemaPropertyViewSet,
                                                UserFactorViewSet,
                                                UserGroupMembershipsViewSet,
                                                UserSchemaPropertyViewSet,
                                                UserTypeViewSet, UserViewSet)

# Dictionary to register all entity viewsets
ENTITY_VIEWSETS = {
    #  "users": BaseUserViewSet,
     "identity_providers": BaseIdentityProviderViewSet,
    "behavior": BehaviorViewSet, 
    "orgs": OrgViewSet,
    "authenticators": BaseAuthenticatorViewSet,
    "groups": BaseGroupViewSet,
    "brands": BaseBrandViewSet,
    "sms_templates": SmsTemplateViewSet,
    "threat_insights": ThreatInsightViewSet,
    "network_zones": NetworkZoneViewSet,
    "inline_hooks": InlineHookEntityViewSet,
    "event_hooks": EventHookViewSet,
    "auth_server": BaseAuthServerViewSet,
    "trusted_origins": TrustedOriginViewSet,
    "device_assurance_policy": BaseDeviceAssurancePolicyViewSet,
    "policies": BasePolicyViewSet,
    "apps": BaseAppViewSet,
    "administrators": BaseAdministratorViewSet,
    "links": BaseLinkViewSet,
    "captchas": BaseCaptchaViewSet,
    "emails": BaseEmailViewSet,
    "rate_limits": BaseRateLimitViewSet,
    "entitlements": BaseEntitlementViewSet,
    "requests": BaseRequestConditionViewSet,
    "catalogs": BaseCatalogViewSet,
    "campaigns": CampaignViewSet
}

GROUP_ENTITY_VIEWSETS = {
    "group": GroupEntityViewSet,
    # "group_memberships": GroupMembershipViewSet,
    # "group_owners": GroupOwnerViewSet,
    "group_roles": GroupRoleViewSet,
    "group_rules": GroupRuleViewSet,
    "group_schemas": GroupSchemaPropertyViewSet
}

AUTH_SERVER_ENTITY_VIEWSETS = {
    "auth_servers": AuthorizationServerViewSet,
    "auth_servers_default": AuthorizationServerDefaultViewSet,
    "auth_server_claims": AuthorizationServerClaimViewSet,
    "auth_server_policy": AuthorizationServerPolicyViewSet,
    "auth_server_policy_rules": AuthorizationServerPolicyRuleViewSet,
    "auth_server_scopes": AuthorizationServerScopeViewSet,
    "auth_trusted_servers": AuthTrustedServerViewSet,
}

USER_ENTITY_VIEWSETS = {
    "users": UserViewSet,
    "user_types": UserTypeViewSet,
    "user_admin_roles": UserAdminRolesViewSet,
    "okta_admin_role_targets": AdminRoleTargetsViewSet,
    "okta_role_subscription": RoleSubscriptionViewSet,
    "user_factors": UserFactorViewSet,
    "user_schema_properties": UserSchemaPropertyViewSet,
    "user_base_schema_property": UserBaseSchemaPropertyViewSet,
    "okta_user_group_memberships": UserGroupMembershipsViewSet
}

IDENTITY_PROVIDER_ENTITY_VIEWSETS = {
    "okta_idp_oidc": IdentityProviderOIDCViewSet,
    "okta_idp_saml": IdentityProviderSAMLViewSet,
    "okta_idp_social": IdentityProviderSocialViewSet
 }

DEVICE_ASSURANCE_POLICY_ENTITY_VIEWSETS = {
    "okta_policy_device_assurance_android": DeviceAndroidViewSet,
    "okta_policy_device_assurance_macos": DeviceMacOSViewSet,
    "okta_policy_device_assurance_windows": DeviceWindowsViewSet,
    "okta_policy_device_assurance_ios": DeviceIOSViewSet,
}

POLICY_ENTITY_VIEWSETS = {
    "okta_policy_mfa": PolicyMFAViewSet,
    "okta_policy_rule_mfa": PolicyRuleMFAViewSet,
    "okta_policy_password": PolicyPasswordViewSet,
    "okta_policy_profile_enrollment": PolicyProfileEnrollmentViewSet,
    "okta_policy_profile_enrollment_apps": PolicyProfileEnrollmentAppsViewSet,
    "okta_policy_rule_idp_discovery": PolicyRuleIDPDiscoveryViewSet,
    "okta_policy_rule_password": PolicyRulePasswordViewSet,
    "okta_policy_rule_profile_enrollment": PolicyRuleProfileEnrollmentViewSet,
    "okta_policy_signon": PolicySignOnViewSet,
    "okta_policy_rule_signon": PolicyRuleSignOnViewSet,
}

EMAIL_ENTITY_VIEWSETS = {
    "okta_email_smtp_server": EmailSmtpServerViewSet,
    # "okta_email_template_Settings": EmailTemplateSettingsViewSet,
    # "okta_email_notifications": EmailSecurityNotificationViewset
}

RATE_LIMIT_ENTITY_VIEWSETS = {
    "okta_principal_rate_limits": PrincipalRateLimitViewSet,
    "okta_rate_limit_admin_notification": RateLimitAdminNotificationViewSet,
    "okta_rate_limit_warning_threshold_percentage": RateLimitWarningThresholdViewSet,
}

BRAND_ENTITY_VIEWSETS = {
    "brands": BrandEntityViewSet,
    "okta_email_domain": EmailDomainViewset,
    "okta_theme": ThemeViewset,
}

AUTHENTICATOR_ENTITY_VIEWSETS = {
    "authenticators": AuthenticatorViewSet,
    "okta_factors": OktaFactorViewSet,
}

APP_ENTITY_VIEWSETS = {
    "okta_app_oauth": AppOauthViewSet,
    "okta_app_saml": AppSAMLViewSet,
    "okta_app_group_assignments": AppGroupAssignmentsViewSet,
    "okta_app_access_policy_assignment": AppAccessPolicyAssignmentViewSet,
    "okta_app_policy_sign_on": AppPolicySignOnViewSet,
    "okta_app_group_assignment": AppsGroupAssignmentViewSet,
    "okta_app_shared_credentials": AppSharedCredentialsViewSet,
    "okta_app_saml_settings": AppSAMLSettingsViewSet,
    "okta_app_signon_policy_rule": AppPolicyRuleSignOnViewSet,
    "okta_app_oauth_role_assignment": AppOauthRoleAssignmentViewSet,
    "okta_app_bookmark": AppBookmarkViewSet,
    "okta_app_auto_login": AppAutoLoginViewSet,
    "okta_app_basic_auth": AppBasicAuthViewSet,
    "okta_app_swa": AppSwaViewSet, 
    "okta_app_users": AppUserViewSet,
    "okta_app_user_base_schema_property": AppUserBaseSchemaPropertyViewSet,
    "okta_app_user_schema_property": AppUserSchemaPropertyViewSet,
    "okta_app_secure_password_store": AppSecurePasswordStoreViewSet,
    "okta_app_three_field": AppThreeFieldViewSet,
    "okta_apps_oauth_post_redirect_uri": AppOauthPostRedirectUriViewSet,
    "okta_apps_oauth_redirect_uri": AppOauthRedirectUriViewSet,
    "okta_app_oauth_api_scope": AppOauthApiScopeViewSet,
}

ADMINISTRATORS_ENTITY_VIEWSETS = {
    "okta_admin_role_custom": AdminRoleCustomViewSet,
    "okta_resource_set": AdminResourceSetViewSet,
}

LINK_ENTITY_VIEWSETS = {"okta_link_definition": OktaLinkDefinitionViewSet}

CAPTCHA_ENTITY_VIEWSETS = {
    "okta_captcha": CaptchaViewSet,
    "okta_captcha_settings": CaptchaOrgWideSettingsViewSet,
}

ENTITLEMENT_ENTITY_VIEWSETS = {
    "okta_entitlement_bundle": EntitlementBundleViewSet,
    "okta_principal_entitlements": PrincipalEntitlementsViewSet,
    "okta_entitlements": EntitlementViewSet,
}

REQUEST_ENTITY_VIEWSETS = {
    "okta_request_conditions": RequestConditionViewSet,
    "okta_request_sequences": RequestSequenceViewSet,
    "okta_request_settings": RequestSettingsViewSet,
    "okta_request_types": RequestTypeViewSet,
}

CATALOG_ENTITY_VIEWSETS = {
    "okta_catalog_entry_default": CatalogEntryDefaultViewSet,
    "okta_catalog_entry_user_access_request_fields": CatalogEntryUserAccessRequestFieldsViewSet,
    "okta_end_user_my_requests": EndUserMyRequestsViewSet,
}
