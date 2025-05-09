from entities.okta_entities.administrators.views.administrators_base_viewset import (
    BaseAdministratorViewSet,
)
from entities.okta_entities.administrators.views.administrators_resourceset_viewset import (
    AdminResourcesetViewSet,
)
from entities.okta_entities.administrators.views.administrators_role_custom_viewset_ import (
    AdminRoleCustomViewSet,
)
from entities.okta_entities.apps.views.app_policy_signon_rule_viewset import (
    AppPolicyRuleSignOnViewSet,
)
from entities.okta_entities.apps.views.app_saml_settings_viewset import (
    AppSAMLSettingsViewSet,
)
from entities.okta_entities.apps.views.app_shared_credentials_viewset import (
    AppSharedCredentialsViewSet,
)
from entities.okta_entities.apps.views.apps_acess_policy_assignment_viewset import (
    AppAcessPolicyAssignmentViewSet,
)
from entities.okta_entities.apps.views.apps_auto_login_viewset import (
    AppAutoLoginViewSet,
)
from entities.okta_entities.apps.views.apps_base_viewset import BaseAppViewSet
from entities.okta_entities.apps.views.apps_basic_auth_viewset import (
    AppBasicAuthViewSet,
)
from entities.okta_entities.apps.views.apps_bookmark_viewset import AppBookmarkViewSet
from entities.okta_entities.apps.views.apps_group_assignment_viewset import (
    AppsGroupAssignmentViewSet,
)
from entities.okta_entities.apps.views.apps_group_assignments_viewset import (
    AppsGroupAssignmentsViewSet,
)
from entities.okta_entities.apps.views.apps_oauth_role_assignment_viewset import (
    AppOauthRoleAssignmentViewSet,
)
from entities.okta_entities.apps.views.apps_oauth_viewset import AppOauthViewSet
from entities.okta_entities.apps.views.apps_policy_signon_viewset import (
    AppPolicySignOnViewSet,
)
from entities.okta_entities.apps.views.apps_saml_viewset import AppSAMLViewSet
from entities.okta_entities.auth_server.views.auth_server_base_viewset import (
    BaseAuthServerViewSet,
)
from entities.okta_entities.auth_server.views.auth_server_claim_viewset import (
    AuthorizationServerClaimViewSet,
)
from entities.okta_entities.auth_server.views.auth_server_default_viewset import (
    AuthorizationServerDefaultViewSet,
)
from entities.okta_entities.auth_server.views.auth_server_policy_rule_viewset import (
    AuthorizationServerPolicyRuleViewSet,
)
from entities.okta_entities.auth_server.views.auth_server_policy_viewset import (
    AuthorizationServerPolicyViewSet,
)
from entities.okta_entities.auth_server.views.auth_server_scope_viewset import (
    AuthorizationServerScopeViewSet,
)
from entities.okta_entities.auth_server.views.auth_server_viewset import (
    AuthorizationServerViewSet,
)
from entities.okta_entities.auth_server.views.auth_trusted_server_viewset import (
    AuthTrustedServerViewSet,
)
from entities.okta_entities.authenticator.views.authenticator_base_viewset import (
    BaseAuthenticatorViewSet,
)
from entities.okta_entities.authenticator.views.authenticator_viewset import (
    AuthenticatorViewSet,
)
from entities.okta_entities.authenticator.views.okta_factor_viewset import (
    OktaFactorViewSet,
)
from entities.okta_entities.behavior.views.behavior_viewset import BehaviorViewSet
from entities.okta_entities.brands.views.brand_base_viewset import BaseBrandViewSet
from entities.okta_entities.brands.views.brand_viewset import BrandEntityViewSet
from entities.okta_entities.brands.views.email_domains_viewset import EmailDomainViewset
from entities.okta_entities.brands.views.okta_theme_viewset import ThemeViewset
from entities.okta_entities.device_assurance_policies.views.device_android_viewset import (
    DeviceAndroidViewSet,
)
from entities.okta_entities.device_assurance_policies.views.device_base_viewset import (
    BaseDeviceAssurancePolicyViewSet,
)
from entities.okta_entities.device_assurance_policies.views.device_ios_viewset import (
    DeviceIOSViewSet,
)
from entities.okta_entities.device_assurance_policies.views.device_macos_viewset import (
    DeviceMacOSViewSet,
)
from entities.okta_entities.device_assurance_policies.views.device_windows_viewset import (
    DeviceWindowsViewSet,
)
from entities.okta_entities.email.views.email_base_viewset import BaseEmailViewSet

# from entities.okta_entities.email.views.email_security_notifications_viewset import (
#     EmailSecurityNotificationViewset,
# )
from entities.okta_entities.event_hook.views.event_hook_viewset import EventHookViewSet
from entities.okta_entities.groups.views.group_base_viewset import BaseGroupViewSet
from entities.okta_entities.groups.views.group_membership_viewset import (
    GroupMembershipViewSet,
)
from entities.okta_entities.groups.views.group_role_viewset import GroupRoleViewSet
from entities.okta_entities.groups.views.group_rule_viewset import GroupRuleViewSet
from entities.okta_entities.groups.views.group_schema_property_viewset import (
    GroupSchemaPropertyViewSet,
)
from entities.okta_entities.groups.views.group_viewset import GroupEntityViewSet
from entities.okta_entities.identity_providers.views.identity_provider_base_viewset import (
    BaseIdentityProviderViewSet,
)
from entities.okta_entities.identity_providers.views.identity_provider_oidc_viewset import (
    IdentityProviderOIDCViewSet,
)
from entities.okta_entities.identity_providers.views.identity_provider_saml_viewset import (
    IdentityProviderSAMLViewSet,
)
from entities.okta_entities.identity_providers.views.identity_provider_social_viewset import (
    IdentityProviderSocialViewSet,
)
from entities.okta_entities.inline_hooks.views.inline_hook_viewset import (
    InlineHookEntityViewSet,
)
from entities.okta_entities.link.views.link_base_viewset import BaseLinkViewSet
from entities.okta_entities.link.views.link_definition_viewset import (
    OktaLinkDefinitionViewSet,
)
from entities.okta_entities.network_zone.views.network_zone_viewset import (
    NetworkZoneViewSet,
)
from entities.okta_entities.org.views.org_viewset import OrgViewSet
from entities.okta_entities.policies.views.policy_base_viewset import BasePolicyViewSet
from entities.okta_entities.policies.views.policy_mfa_viewset import PolicyMFAViewSet
from entities.okta_entities.policies.views.policy_password_viewset import (
    PolicyPasswordViewSet,
)
from entities.okta_entities.policies.views.policy_profile_enrollment_apps_viewset import (
    PolicyProfileEnrollmentAppsViewSet,
)
from entities.okta_entities.policies.views.policy_profile_enrollment_viewset import (
    PolicyProfileEnrollmentViewSet,
)
from entities.okta_entities.policies.views.policy_rule_idp_discovery_viewset import (
    PolicyRuleIDPDiscoveryViewSet,
)
from entities.okta_entities.policies.views.policy_rule_mfa_viewset import (
    PolicyRuleMFAViewSet,
)
from entities.okta_entities.policies.views.policy_rule_password_viewset import (
    PolicyRulePasswordViewSet,
)
from entities.okta_entities.policies.views.policy_rule_profile_enrollment_viewset import (
    PolicyRuleProfileEnrollmentViewSet,
)
from entities.okta_entities.policies.views.policy_rule_signon_viewset import (
    PolicyRuleSignOnViewSet,
)
from entities.okta_entities.policies.views.policy_signon_viewset import (
    PolicySignOnViewSet,
)
from entities.okta_entities.sms_templates.views.sms_template_viewset import (
    SmsTemplateViewSet,
)
from entities.okta_entities.threat_insights.views.threat_insight_viewset import (
    ThreatInsightViewSet,
)
from entities.okta_entities.trusted_origins.views.trusted_origin_viewset import (
    TrustedOriginViewSet,
)

# from entities.okta_entities.users.views.role_subscription_viewset import RoleSubscriptionViewSet
from entities.okta_entities.users.views.admin_role_targets_viewset import (
    AdminRoleTargetsViewSet,
)
from entities.okta_entities.users.views.role_subscription_viewset import (
    RoleSubscriptionViewSet,
)
from entities.okta_entities.users.views.user_admin_roles_viewset import (
    UserAdminRolesViewSet,
)
from entities.okta_entities.users.views.user_base_schema_property_viewset import (
    UserBaseSchemaPropertyViewSet,
)
from entities.okta_entities.users.views.user_base_viewset import BaseUserViewSet
from entities.okta_entities.users.views.user_factor_viewset import UserFactorViewSet
from entities.okta_entities.users.views.user_group_memberships_viewset import (
    UserGroupMembershipsViewSet,
)
from entities.okta_entities.users.views.user_schema_property_viewset import (
    UserSchemaPropertyViewSet,
)
from entities.okta_entities.users.views.user_type_viewset import UserTypeViewSet
from entities.okta_entities.users.views.user_viewset import UserViewSet

# Dictionary to register all entity viewsets
ENTITY_VIEWSETS = {
    "users": BaseUserViewSet,
    "identity_providers": BaseIdentityProviderViewSet,
    #   "roles": AdministrativeRoleEntityViewSet,
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
}

GROUP_ENTITY_VIEWSETS = {
    "groups": GroupEntityViewSet,
    "group_memberships": GroupMembershipViewSet,
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
    # "user_admin_roles": UserAdminRolesViewSet,
    # "okta_admin_role_targets": AdminRoleTargetsViewSet,
    # "okta_role_subscription": RoleSubscriptionViewSet,
    # "user_factors": UserFactorViewSet,
    "user_schema_properties": UserSchemaPropertyViewSet,
    "user_base_schema_property": UserBaseSchemaPropertyViewSet,
    # "okta_user_group_memberships": UserGroupMembershipsViewSet
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
    "apps_access_policy_assignment": AppAcessPolicyAssignmentViewSet,
    "okta_app_policy_sign_on": AppPolicySignOnViewSet,
    "okta_apps_group_assignment": AppsGroupAssignmentViewSet,
    "okta_app_shared_credentials": AppSharedCredentialsViewSet,
    "okta_app_saml_settings": AppSAMLSettingsViewSet,
    "okta_app_signon_policy_rule": AppPolicyRuleSignOnViewSet,
    "okta_app_oauth_role_assignment": AppOauthRoleAssignmentViewSet,
    "okta_app_bookmark": AppBookmarkViewSet,
    "okta_app_auto_login": AppAutoLoginViewSet,
    "okta_app_basic_auth": AppBasicAuthViewSet
}


ADMINISTRATORS_ENTITY_VIEWSETS = {
    "okta_admin_role_custom": AdminRoleCustomViewSet,
    "okta_resource_set": AdminResourcesetViewSet
}

LINK_ENTITY_VIEWSETS = {
    "okta_link_definition": OktaLinkDefinitionViewSet
}
