
from entities.okta_entities.trusted_origins.views import (
    TrustedOriginViewSet,
)
from entities.okta_entities.inline_hooks.views import (
    InlineHookEntityViewSet
    )
from entities.okta_entities.identity_providers.views import (
    BaseIdentityProviderViewSet, 
    IdentityProviderOIDCViewSet, 
    IdentityProviderSAMLViewSet, 
    IdentityProviderSocialViewSet
)
from entities.okta_entities.link.views import (
    OktaLinkDefinitionViewSet,
    BaseLinkViewSet
)
from entities.okta_entities.administrators.views import (
    BaseAdministratorViewSet,
    AdminResourceSetViewSet,
    AdminRoleCustomViewSet,
)
from entities.okta_entities.network_zone.views import(
    NetworkZoneViewSet,
)
from entities.okta_entities.org.views import ( 
    OrgViewSet
)
from entities.okta_entities.policies.views import (
    BasePolicyViewSet,
    PolicyPasswordViewSet,
    PolicyMFAViewSet,
    PolicyProfileEnrollmentViewSet,
    PolicyProfileEnrollmentAppsViewSet,
    PolicyRuleIDPDiscoveryViewSet,
    PolicyRuleMFAViewSet,
    PolicyRulePasswordViewSet,
    PolicyRuleProfileEnrollmentViewSet,
    PolicyRuleSignOnViewSet,
    PolicySignOnViewSet,
)
from entities.okta_entities.sms_templates.views import (
    SmsTemplateViewSet,
)
from entities.okta_entities.threat_insights.views import (
    ThreatInsightViewSet,
)
from entities.okta_entities.users.views import (
    AdminRoleTargetsViewSet,
    RoleSubscriptionViewSet,
    UserAdminRolesViewSet,
    UserBaseSchemaPropertyViewSet,
    BaseUserViewSet,
    UserFactorViewSet,
    UserGroupMembershipsViewSet,
    UserSchemaPropertyViewSet,
    UserTypeViewSet,
    UserViewSet
)

from entities.okta_entities.apps.views import (
    AppOauthApiScopeViewSet,
    AppOauthPostRedirectUriViewSet,
    AppOauthRedirectUriViewSet,
    AppPolicyRuleSignOnViewSet,
    AppSAMLSettingsViewSet,
    AppSharedCredentialsViewSet,
    AppUserBaseSchemaPropertyViewSet,
    AppUserViewSet,
    AppAccessPolicyAssignmentViewSet,
    AppAutoLoginViewSet,
    BaseAppViewSet,
    AppBasicAuthViewSet,
    AppBookmarkViewSet,
    AppsGroupAssignmentViewSet,
    AppsGroupAssignmentsViewSet,
    AppOauthRoleAssignmentViewSet,
    AppOauthViewSet,
    AppPolicySignOnViewSet,
    AppSAMLViewSet,
    AppSwaViewSet,
)

from entities.okta_entities.auth_server.views import (
    BaseAuthServerViewSet,
    AuthorizationServerClaimViewSet,
    AuthorizationServerDefaultViewSet,
    AuthorizationServerPolicyViewSet,
    AuthorizationServerPolicyRuleViewSet,
    AuthorizationServerScopeViewSet,
    AuthorizationServerViewSet,
    AuthTrustedServerViewSet,
    AuthorizationServerClaimDefaultViewSet,
)
from entities.okta_entities.authenticator.views import (
     BaseAuthenticatorViewSet,
     AuthenticatorViewSet,
     OktaFactorViewSet,
)
from entities.okta_entities.behavior.views import(
     BehaviorViewSet
)
from entities.okta_entities.brands.views import ( 
    BaseBrandViewSet,
    BrandEntityViewSet,
    EmailDomainViewset,
    ThemeViewset
)
from entities.okta_entities.captchas.views import (
    BaseCaptchaViewSet,
    CaptchaOrgWideSettingsViewSet,
    CaptchaViewSet
)
from entities.okta_entities.device_assurance_policies.views import (
    DeviceAndroidViewSet,
    BaseDeviceAssurancePolicyViewSet,
    DeviceIOSViewSet,
    DeviceMacOSViewSet,
    DeviceWindowsViewSet
)
from entities.okta_entities.email.views import (
    BaseEmailViewSet
)
from entities.okta_entities.event_hook.views import(
   EventHookViewSet
)
from entities.okta_entities.groups.views import (
    BaseGroupViewSet,
    GroupRoleViewSet,
    GroupRuleViewSet,
    GroupSchemaPropertyViewSet,
    GroupEntityViewSet,
    GroupMembershipViewSet,
    GroupOwnerViewSet,
)
# Dictionary to register all entity viewsets
ENTITY_VIEWSETS = {
#      "users": BaseUserViewSet,
#     "identity_providers": BaseIdentityProviderViewSet,
#     "behavior": BehaviorViewSet, 
#     "orgs": OrgViewSet,
#     "authenticators": BaseAuthenticatorViewSet,
#     "groups": BaseGroupViewSet,
#     "brands": BaseBrandViewSet,
#     "sms_templates": SmsTemplateViewSet,
#     "threat_insights": ThreatInsightViewSet,
#     "network_zones": NetworkZoneViewSet,
#     "inline_hooks": InlineHookEntityViewSet,
#     "event_hooks": EventHookViewSet,
#     "auth_server": BaseAuthServerViewSet,
#     "trusted_origins": TrustedOriginViewSet,
#     "device_assurance_policy": BaseDeviceAssurancePolicyViewSet,
#     "policies": BasePolicyViewSet,
#     "apps": BaseAppViewSet,
#     "administrators": BaseAdministratorViewSet,
#     "links": BaseLinkViewSet,
#     "captchas": BaseCaptchaViewSet,
#     "users": BaseUserViewSet,
#     "identity_providers": BaseIdentityProviderViewSet,
#     "behavior": BehaviorViewSet, 
#     "orgs": OrgViewSet,
#     "authenticators": BaseAuthenticatorViewSet,
#     "groups": BaseGroupViewSet,
#     "brands": BaseBrandViewSet,
#     "sms_templates": SmsTemplateViewSet,
#     "threat_insights": ThreatInsightViewSet,
#     "network_zones": NetworkZoneViewSet,
#       "inline_hooks": InlineHookEntityViewSet,
#     "event_hooks": EventHookViewSet,
#      "auth_server": BaseAuthServerViewSet,
#     "trusted_origins": TrustedOriginViewSet,
#     "device_assurance_policy": BaseDeviceAssurancePolicyViewSet,
#     "policies": BasePolicyViewSet,
#      "apps": BaseAppViewSet,
#     "administrators": BaseAdministratorViewSet,
#      "links": BaseLinkViewSet,
    "captchas": BaseCaptchaViewSet,
    # "emails": BaseEmailViewSet
}

GROUP_ENTITY_VIEWSETS = {
    "group": GroupEntityViewSet,
    "group_memberships": GroupMembershipViewSet,
    #"group_owners": GroupOwnerViewSet,
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
    "okta_user_group_memberships": UserGroupMembershipsViewSet,
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
    "okta_policy_device_assurance_ios": DeviceIOSViewSet
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
    # "okta_email_template_Settings": EmailTemplateSettingsViewSet,
    # "okta_email_notifications": EmailSecurityNotificationViewset
}

BRAND_ENTITY_VIEWSETS = {
    "brands": BrandEntityViewSet,
    "okta_email_domain": EmailDomainViewset,
    "okta_theme": ThemeViewset
}

AUTHENTICATOR_ENTITY_VIEWSETS = {
    "authenticators": AuthenticatorViewSet,
    "okta_factors": OktaFactorViewSet,
}

APP_ENTITY_VIEWSETS = {
    "okta_app_oauth": AppOauthViewSet,
    "okta_app_saml": AppSAMLViewSet,
    "okta_apps_group_assignments": AppsGroupAssignmentsViewSet,
    "apps_access_policy_assignment": AppAccessPolicyAssignmentViewSet,
    "okta_app_policy_sign_on": AppPolicySignOnViewSet,
    "okta_apps_group_assignment": AppsGroupAssignmentViewSet,
    "okta_app_shared_credentials": AppSharedCredentialsViewSet,
    "okta_app_saml_settings": AppSAMLSettingsViewSet,
    "okta_app_signon_policy_rule": AppPolicyRuleSignOnViewSet,
    "okta_app_oauth_role_assignment": AppOauthRoleAssignmentViewSet,
    "okta_app_bookmark": AppBookmarkViewSet,
    "okta_app_auto_login": AppAutoLoginViewSet,
    "okta_app_basic_auth": AppBasicAuthViewSet,
    "okta_app_swa": AppSwaViewSet,
    "okta_app_users": AppUserViewSet,
    "okta_apps_oauth_api_scope": AppOauthApiScopeViewSet,
    "okta_apps_oauth_post_redirect_uri": AppOauthPostRedirectUriViewSet,
    "okta_apps_oauth_redirect_uri": AppOauthRedirectUriViewSet,
    "okta_app_user_base_schema_property": AppUserBaseSchemaPropertyViewSet
}

ADMINISTRATORS_ENTITY_VIEWSETS = {
    "okta_admin_role_custom": AdminRoleCustomViewSet,
    "okta_resource_set": AdminResourceSetViewSet
}

LINK_ENTITY_VIEWSETS = {
    "okta_link_definition": OktaLinkDefinitionViewSet
}

CAPTCHA_ENTITY_VIEWSETS = {
    "okta_captcha": CaptchaViewSet,
    "okta_captcha_settings": CaptchaOrgWideSettingsViewSet
}
