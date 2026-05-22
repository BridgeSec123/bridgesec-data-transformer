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
from entities.okta_entities.apps.views.app_token_viewset import AppTokenViewSet
from entities.okta_entities.apps.views.app_connection_viewset import AppConnectionViewSet
from entities.okta_entities.apps.views.app_federated_claim_viewset import AppFederatedClaimViewSet
from entities.okta_entities.apps.views.app_push_groups_viewset import AppPushGroupsViewSet
from entities.okta_entities.push_providers.views import PushProviderViewSet
from entities.okta_entities.api_service_integrations.views import ApiServiceIntegrationViewSet
from entities.okta_entities.ui_schemas.views import UiSchemaViewSet
from entities.okta_entities.apps.views.apps_basic_auth_viewset import \
    AppBasicAuthViewSet
from entities.okta_entities.auth_server.views import (
    AuthorizationServerClaimDefaultViewSet, AuthorizationServerClaimViewSet,
    AuthorizationServerClientsViewSet, AuthorizationServerDefaultViewSet,
    AuthorizationServerKeysViewSet, AuthorizationServerPolicyRuleViewSet,
    AuthorizationServerPolicyViewSet, AuthorizationServerScopeViewSet,
    AuthorizationServerViewSet, AuthTrustedServerViewSet, BaseAuthServerViewSet)
from entities.okta_entities.authenticator.views import (
    AuthenticatorViewSet, BaseAuthenticatorViewSet, OktaFactorViewSet)
from entities.okta_entities.behavior.views import BehaviorViewSet
from entities.okta_entities.domain.views import DomainViewSet
from entities.okta_entities.hook_keys.views import HookKeyViewSet
from entities.okta_entities.api_tokens.views import ApiTokenViewSet
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
from entities.okta_entities.entity_risk_policy.views import (
    BaseEntityRiskPolicyViewSet, EntityRiskPolicyViewSet, EntityRiskPolicyRuleViewSet)
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
from entities.okta_entities.reviews.views import ReviewViewSet
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
                                                UserRiskViewSet,
                                                UserSchemaPropertyViewSet,
                                                UserTypeViewSet, UserViewSet)

# Dictionary to register all entity viewsets
ENTITY_VIEWSETS = {
    "users": BaseUserViewSet,
    "identity_providers": BaseIdentityProviderViewSet,
    "behavior": BehaviorViewSet,
    # "domains": DomainViewSet,
    # "hook_keys": HookKeyViewSet,
    # "api_tokens": ApiTokenViewSet,
    # "push_providers": PushProviderViewSet,
    # "api_service_integrations": ApiServiceIntegrationViewSet,
    # "ui_schemas": UiSchemaViewSet,
    "orgs": OrgViewSet,
    "authenticators": BaseAuthenticatorViewSet,
    "groups": BaseGroupViewSet,
    "brands": BaseBrandViewSet,
    # "sms_templates": SmsTemplateViewSet,
    "threat_insights": ThreatInsightViewSet,
    # "network_zones": NetworkZoneViewSet,
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
    "reviews": ReviewViewSet,
    "requests": BaseRequestConditionViewSet,
    "catalogs": BaseCatalogViewSet,
    "campaigns": CampaignViewSet,
    # "entity_risk_policy": BaseEntityRiskPolicyViewSet,
}

GROUP_ENTITY_VIEWSETS = {
    "group": GroupEntityViewSet,
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
    "auth_server_clients": AuthorizationServerClientsViewSet,
    "auth_server_keys": AuthorizationServerKeysViewSet,
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
    "okta_user_risk": UserRiskViewSet,
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
    # "okta_policy_rule_idp_discovery": PolicyRuleIDPDiscoveryViewSet,
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
    "okta_app_saml_app_settings": AppSAMLSettingsViewSet,
    "okta_app_signon_policy_rule": AppPolicyRuleSignOnViewSet,
    "okta_app_oauth_role_assignment": AppOauthRoleAssignmentViewSet,
    "okta_app_bookmark": AppBookmarkViewSet,
    "okta_app_auto_login": AppAutoLoginViewSet,
    "okta_app_basic_auth": AppBasicAuthViewSet,
    "okta_app_swa": AppSwaViewSet,
    "okta_app_user": AppUserViewSet,
    "okta_app_user_base_schema_property": AppUserBaseSchemaPropertyViewSet,
    "okta_app_user_schema_property": AppUserSchemaPropertyViewSet,
    "okta_app_secure_password_store": AppSecurePasswordStoreViewSet,
    "okta_app_three_field": AppThreeFieldViewSet,
    "okta_apps_oauth_post_redirect_uri": AppOauthPostRedirectUriViewSet,
    "okta_apps_oauth_redirect_uri": AppOauthRedirectUriViewSet,
    "okta_app_oauth_api_scope": AppOauthApiScopeViewSet,
    "okta_app_token": AppTokenViewSet,
    "okta_app_connection": AppConnectionViewSet,
    "okta_app_federated_claim": AppFederatedClaimViewSet,
    "okta_app_push_groups": AppPushGroupsViewSet,
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

ENTITY_RISK_POLICY_VIEWSETS = {
    "okta_entity_risk_policy": EntityRiskPolicyViewSet,
    "okta_entity_risk_policy_rule": EntityRiskPolicyRuleViewSet,
}


# ---------------------------------------------------------------------------
# FULL_ENTITY_REGISTRY
# ---------------------------------------------------------------------------
# Complete catalog of every entity group — including those currently commented
# out of ENTITY_VIEWSETS. Used exclusively by the seed_entity_catalog command
# and the entity-config API to populate Supabase. Never used for runtime
# backup dispatch (that uses ENTITY_VIEWSETS).
#
# is_active=True  → available for tenant backup selection
# is_active=False → visible in UI as "not yet available"
#
# collections → list of MongoDB collections produced by this entity group.
# Each entry: {display_name, collection_name, id_field}
# ---------------------------------------------------------------------------
FULL_ENTITY_REGISTRY = {
    "users": {
        "display_name": "Users",
        "category": "Identity",
        "is_active": True,
        "description": "Okta users, user types, schema properties, admin roles, factors, group memberships",
        "collections": [
            {"display_name": "Users",                     "collection_name": "okta_user",                      "id_field": "user_id"},
            {"display_name": "User Types",                "collection_name": "okta_user_type",                 "id_field": "user_type_id"},
            {"display_name": "User Schema Properties",    "collection_name": "okta_user_schema_property",      "id_field": "user_id"},
            {"display_name": "User Base Schema Props",    "collection_name": "okta_user_base_schema_property", "id_field": "user_id"},
            {"display_name": "User Admin Roles",          "collection_name": "okta_user_admin_roles",          "id_field": "user_id"},
            {"display_name": "User Group Memberships",    "collection_name": "okta_user_group_memberships",    "id_field": "user_id"},
            {"display_name": "User Risk",                 "collection_name": "okta_user_risk",                 "id_field": "user_id"},
        ],
    },
    "groups": {
        "display_name": "Groups",
        "category": "Identity",
        "is_active": True,
        "description": "Okta groups, group rules, roles, memberships, schema",
        "collections": [
            {"display_name": "Groups",             "collection_name": "okta_group",             "id_field": "group_id"},
            {"display_name": "Group Rules",        "collection_name": "okta_group_rule",         "id_field": "group_rule_id"},
            {"display_name": "Group Roles",        "collection_name": "okta_group_role",         "id_field": "group_role_id"},
            {"display_name": "Group Memberships",  "collection_name": "okta_group_memberships",  "id_field": "group_id"},
            {"display_name": "Group Schema",       "collection_name": "okta_group_schema_property", "id_field": "id"},
        ],
    },
    "apps": {
        "display_name": "Applications",
        "category": "Applications",
        "is_active": True,
        "description": "All Okta app types — OAuth, SAML, SWA, Bookmark, Basic Auth and related sub-entities",
        "collections": [
            {"display_name": "App OAuth",                    "collection_name": "okta_app_oauth",                      "id_field": "app_id"},
            {"display_name": "App SAML",                     "collection_name": "okta_app_saml",                       "id_field": "app_id"},
            {"display_name": "App SAML Settings",            "collection_name": "okta_app_saml_app_settings",          "id_field": "app_id"},
            {"display_name": "App Bookmark",                 "collection_name": "okta_app_bookmark",                   "id_field": "app_id"},
            {"display_name": "App Auto Login",               "collection_name": "okta_app_auto_login",                 "id_field": "app_id"},
            {"display_name": "App Basic Auth",               "collection_name": "okta_app_basic_auth",                 "id_field": "app_id"},
            {"display_name": "App SWA",                      "collection_name": "okta_app_swa",                        "id_field": "app_id"},
            {"display_name": "App Three Field",              "collection_name": "okta_app_three_field",                "id_field": "app_id"},
            {"display_name": "App Secure Password Store",    "collection_name": "okta_app_secure_password_store",      "id_field": "app_id"},
            {"display_name": "App Group Assignments",        "collection_name": "okta_app_group_assignments",          "id_field": "app_id"},
            {"display_name": "App Group Assignment",         "collection_name": "okta_app_group_assignment",           "id_field": "app_id"},
            {"display_name": "App Signon Policy",            "collection_name": "okta_app_signon_policy",              "id_field": "app_policy_id"},
            {"display_name": "App Signon Policy Rule",       "collection_name": "okta_app_signon_policy_rule",         "id_field": "policy_rule_id"},
            {"display_name": "App Access Policy Assignment", "collection_name": "okta_app_access_policy_assignment",   "id_field": "app_id"},
            {"display_name": "App OAuth Role Assignment",    "collection_name": "okta_app_oauth_role_assignment",      "id_field": "client_id"},
            {"display_name": "App OAuth Api Scope",          "collection_name": "okta_app_oauth_api_scope",            "id_field": "app_id"},
            {"display_name": "App OAuth Redirect Uri",       "collection_name": "okta_app_oauth_redirect_uri",         "id_field": "app_id"},
            {"display_name": "App OAuth Post Redirect Uri",  "collection_name": "okta_apps_oauth_post_redirect_uri",   "id_field": "app_id"},
            {"display_name": "App Shared Credentials",       "collection_name": "okta_app_shared_credentials",         "id_field": "label"},
            {"display_name": "App User",                     "collection_name": "okta_app_user",                       "id_field": "user_id"},
            {"display_name": "App User Schema Property",     "collection_name": "okta_app_user_schema_property",       "id_field": "app_id"},
            {"display_name": "App User Base Schema Prop",    "collection_name": "okta_app_user_base_schema_property",  "id_field": "app_id"},
            {"display_name": "App Token",                    "collection_name": "okta_app_token",                      "id_field": "token_id"},
            {"display_name": "App Connection",               "collection_name": "okta_app_connection",                 "id_field": "app_id"},
            {"display_name": "App Federated Claim",          "collection_name": "okta_app_federated_claim",            "id_field": "claim_id"},
            {"display_name": "App Push Groups",              "collection_name": "okta_app_push_groups",                "id_field": "push_group_id"},
        ],
    },
    "policies": {
        "display_name": "Policies",
        "category": "Policies",
        "is_active": True,
        "description": "MFA, Password, Sign-On and Profile Enrollment policies with their rules",
        "collections": [
            {"display_name": "Policy MFA",                    "collection_name": "okta_policy_mfa",                       "id_field": "policy_id"},
            {"display_name": "Policy MFA Rule",               "collection_name": "okta_policy_rule_mfa",                  "id_field": "policy_rule_id"},
            {"display_name": "Policy Password",               "collection_name": "okta_policy_password",                  "id_field": "policy_id"},
            {"display_name": "Policy Password Rule",          "collection_name": "okta_policy_rule_password",             "id_field": "policy_password_id"},
            {"display_name": "Policy Sign-On",                "collection_name": "okta_policy_signon",                    "id_field": "policy_signon_id"},
            {"display_name": "Policy Sign-On Rule",           "collection_name": "okta_policy_rule_signon",               "id_field": "policy_rule_id"},
            {"display_name": "Policy Profile Enrollment",     "collection_name": "okta_policy_profile_enrollment",        "id_field": "policy_id"},
            {"display_name": "Policy Profile Enroll Rule",    "collection_name": "okta_policy_rule_profile_enrollment",   "id_field": "policy_profile_rule_id"},
            {"display_name": "Policy Profile Enroll Apps",    "collection_name": "okta_policy_profile_enrollment_apps",   "id_field": "policy_id"},
        ],
    },
    "auth_server": {
        "display_name": "Authorization Servers",
        "category": "Authorization",
        "is_active": True,
        "description": "Custom authorization servers with scopes, claims, policies and trusted servers",
        "collections": [
            {"display_name": "Auth Server",            "collection_name": "okta_auth_server",             "id_field": "auth_server_id"},
            {"display_name": "Auth Server Claim",      "collection_name": "okta_auth_server_claim",       "id_field": "auth_server_id"},
            {"display_name": "Auth Server Policy",     "collection_name": "okta_auth_server_policy",      "id_field": "auth_server_id"},
            {"display_name": "Auth Server Policy Rule","collection_name": "okta_auth_server_policy_rule", "id_field": "auth_server_id"},
            {"display_name": "Auth Server Scope",      "collection_name": "okta_auth_server_scope",       "id_field": "auth_server_id"},
            {"display_name": "Auth Server Client",     "collection_name": "okta_auth_server_clients",     "id_field": "token_id"},
            {"display_name": "Auth Server Key",        "collection_name": "okta_auth_server_keys",        "id_field": "key_id"},
            {"display_name": "Auth Trusted Server",    "collection_name": "okta_trusted_server",          "id_field": "auth_server_id"},
        ],
    },
    "identity_providers": {
        "display_name": "Identity Providers",
        "category": "Identity",
        "is_active": True,
        "description": "OIDC, SAML and Social identity provider configurations",
        "collections": [
            {"display_name": "IDP OIDC",   "collection_name": "okta_idp_oidc",   "id_field": "idp_id"},
            {"display_name": "IDP SAML",   "collection_name": "okta_idp_saml",   "id_field": "idp_id"},
            {"display_name": "IDP Social", "collection_name": "okta_idp_social", "id_field": "idp_id"},
        ],
    },
    "authenticators": {
        "display_name": "Authenticators",
        "category": "Security",
        "is_active": True,
        "description": "Okta authenticators and factors",
        "collections": [
            {"display_name": "Authenticator", "collection_name": "okta_authenticator", "id_field": "key"},
            {"display_name": "Factor",        "collection_name": "okta_factor",         "id_field": "provider_id"},
        ],
    },
    "device_assurance_policy": {
        "display_name": "Device Assurance Policies",
        "category": "Policies",
        "is_active": True,
        "description": "Device assurance policies for Android, iOS, macOS and Windows",
        "collections": [
            {"display_name": "Device Android", "collection_name": "okta_policy_device_assurance_android", "id_field": "device_id"},
            {"display_name": "Device iOS",     "collection_name": "okta_policy_device_assurance_ios",     "id_field": "device_id"},
            {"display_name": "Device macOS",   "collection_name": "okta_policy_device_assurance_macos",   "id_field": "device_id"},
            {"display_name": "Device Windows", "collection_name": "okta_policy_device_assurance_windows", "id_field": "device_id"},
        ],
    },
    "brands": {
        "display_name": "Brands & Themes",
        "category": "Branding",
        "is_active": True,
        "description": "Okta org branding, email domains and themes",
        "collections": [
            {"display_name": "Brand",        "collection_name": "okta_brand",        "id_field": "brand_id"},
            {"display_name": "Email Domain", "collection_name": "okta_email_domain", "id_field": "email_domain_id"},
            {"display_name": "Theme",        "collection_name": "okta_theme",         "id_field": "brand_id"},
        ],
    },
    "trusted_origins": {
        "display_name": "Trusted Origins",
        "category": "Security",
        "is_active": True,
        "description": "Trusted origins for CORS and iFrame embedding",
        "collections": [
            {"display_name": "Trusted Origin", "collection_name": "okta_trusted_origin", "id_field": "trusted_id"},
        ],
    },
    "inline_hooks": {
        "display_name": "Inline Hooks",
        "category": "Hooks",
        "is_active": True,
        "description": "Inline hooks for extending Okta workflows",
        "collections": [
            {"display_name": "Inline Hook", "collection_name": "okta_inline_hook", "id_field": "inline_hook_id"},
        ],
    },
    "event_hooks": {
        "display_name": "Event Hooks",
        "category": "Hooks",
        "is_active": True,
        "description": "Event hooks for subscribing to Okta event streams",
        "collections": [
            {"display_name": "Event Hook", "collection_name": "okta_event_hook", "id_field": "event_id"},
        ],
    },
    "orgs": {
        "display_name": "Organization",
        "category": "Administration",
        "is_active": True,
        "description": "Org-level security and configuration settings",
        "collections": [
            {"display_name": "Organization Security", "collection_name": "okta_org_configuration", "id_field": "id"},
        ],
    },
    "behavior": {
        "display_name": "Behaviors",
        "category": "Security",
        "is_active": True,
        "description": "Okta behavior detection rules",
        "collections": [
            {"display_name": "Behavior", "collection_name": "okta_behavior", "id_field": "behavior_id"},
        ],
    },
    "threat_insights": {
        "display_name": "Threat Insights",
        "category": "Security",
        "is_active": True,
        "description": "Threat Insights configuration and settings",
        "collections": [
            {"display_name": "Threat Insights", "collection_name": "okta_threat_insight_settings", "id_field": "action"},
        ],
    },
    "administrators": {
        "display_name": "Administrator Roles",
        "category": "Administration",
        "is_active": True,
        "description": "Custom admin roles and resource sets",
        "collections": [
            {"display_name": "Admin Role Custom", "collection_name": "okta_admin_role_custom", "id_field": "custom_role_id"},
            {"display_name": "Resource Set",      "collection_name": "okta_resource_set",      "id_field": "custom_role_id"},
        ],
    },
    "emails": {
        "display_name": "Email Configuration",
        "category": "Administration",
        "is_active": True,
        "description": "Email SMTP server configuration",
        "collections": [
            {"display_name": "Email SMTP Server", "collection_name": "okta_email_smtp_server", "id_field": "id"},
        ],
    },
    "rate_limits": {
        "display_name": "Rate Limits",
        "category": "Administration",
        "is_active": True,
        "description": "Principal rate limits, admin notifications and warning thresholds",
        "collections": [
            {"display_name": "Principal Rate Limit",      "collection_name": "okta_principal_rate_limits",                    "id_field": "rate_limit_id"},
            {"display_name": "Rate Limit Notification",   "collection_name": "okta_rate_limit_admin_notification",            "id_field": "notification_id"},
            {"display_name": "Rate Limit Warning",        "collection_name": "okta_rate_limit_warning_threshold_percentage",  "id_field": "threshold_id"},
        ],
    },
    "entitlements": {
        "display_name": "Entitlements",
        "category": "Administration",
        "is_active": True,
        "description": "Entitlement bundles, principal entitlements",
        "collections": [
            {"display_name": "Entitlement Bundle",     "collection_name": "okta_entitlement_bundle",      "id_field": "bundle_id"},
            {"display_name": "Principal Entitlement",  "collection_name": "okta_principal_entitlements",  "id_field": "entitlement_id"},
            {"display_name": "Entitlements",           "collection_name": "okta_entitlements",            "id_field": "id"},
        ],
    },
    "links": {
        "display_name": "Links",
        "category": "Administration",
        "is_active": True,
        "description": "Okta link definitions for user relationships",
        "collections": [
            {"display_name": "Link Definition", "collection_name": "okta_link_definition", "id_field": "primary_name"},
        ],
    },
    "captchas": {
        "display_name": "Captchas",
        "category": "Security",
        "is_active": True,
        "description": "CAPTCHA configurations and org-wide settings",
        "collections": [
            {"display_name": "Captcha",          "collection_name": "okta_captcha",                  "id_field": "id"},
            {"display_name": "Captcha Settings", "collection_name": "okta_captcha_org_wide_settings", "id_field": "id"},
        ],
    },
    "reviews": {
        "display_name": "Reviews",
        "category": "Administration",
        "is_active": True,
        "description": "Okta access certification reviews",
        "collections": [
            {"display_name": "Review", "collection_name": "okta_reviews", "id_field": "review_id"},
        ],
    },
    "requests": {
        "display_name": "Requests",
        "category": "Administration",
        "is_active": True,
        "description": "Request conditions, sequences, settings and types",
        "collections": [
            {"display_name": "Request Condition", "collection_name": "okta_request_conditions", "id_field": "condition_id"},
            {"display_name": "Request Sequence",  "collection_name": "okta_request_sequences",  "id_field": "sequence_id"},
            {"display_name": "Request Settings",  "collection_name": "okta_request_settings",   "id_field": "id"},
            {"display_name": "Request Type",      "collection_name": "okta_request_types",       "id_field": "request_id"},
        ],
    },
    "catalogs": {
        "display_name": "Catalogs",
        "category": "Administration",
        "is_active": True,
        "description": "App catalog entries and end-user request access",
        "collections": [
            {"display_name": "Catalog Entry Default",       "collection_name": "okta_catalog_entry_default",                          "id_field": "entry_id"},
            {"display_name": "Catalog Entry Access Fields", "collection_name": "okta_catalog_entry_user_access_request_fields",        "id_field": "field_id"},
            {"display_name": "End User My Requests",        "collection_name": "okta_end_user_my_requests",                           "id_field": "request_id"},
        ],
    },
    "campaigns": {
        "display_name": "Campaigns",
        "category": "Administration",
        "is_active": True,
        "description": "Okta access certification campaigns",
        "collections": [
            {"display_name": "Campaign", "collection_name": "okta_campaign", "id_field": "id"},
        ],
    },
    # ── Inactive entities (commented out in ENTITY_VIEWSETS) ──────────────
    "domains": {
        "display_name": "Domains",
        "category": "Security",
        "is_active": False,
        "description": "Custom domain configurations",
        "collections": [
            {"display_name": "Domain", "collection_name": "okta_domain", "id_field": "domain_id"},
        ],
    },
    "hook_keys": {
        "display_name": "Hook Keys",
        "category": "Hooks",
        "is_active": False,
        "description": "Keys used to sign hook payloads",
        "collections": [
            {"display_name": "Hook Key", "collection_name": "okta_hook_key", "id_field": "hook_key_id"},
        ],
    },
    "api_tokens": {
        "display_name": "API Tokens",
        "category": "Security",
        "is_active": False,
        "description": "Okta API tokens issued to admin users",
        "collections": [
            {"display_name": "API Token", "collection_name": "okta_api_token", "id_field": "token_id"},
        ],
    },
    "push_providers": {
        "display_name": "Push Providers",
        "category": "Security",
        "is_active": False,
        "description": "Push notification provider configurations",
        "collections": [
            {"display_name": "Push Provider", "collection_name": "okta_push_provider", "id_field": "push_provider_id"},
        ],
    },
    "api_service_integrations": {
        "display_name": "API Service Integrations",
        "category": "Administration",
        "is_active": False,
        "description": "Third-party API service integration configurations",
        "collections": [
            {"display_name": "API Service Integration", "collection_name": "okta_api_service_integration", "id_field": "api_service_integration_id"},
        ],
    },
    "ui_schemas": {
        "display_name": "UI Schemas",
        "category": "Branding",
        "is_active": False,
        "description": "UI schema configurations for enrollment flows",
        "collections": [
            {"display_name": "UI Schema", "collection_name": "okta_ui_schema", "id_field": "ui_schema_id"},
        ],
    },
    "sms_templates": {
        "display_name": "SMS Templates",
        "category": "Administration",
        "is_active": False,
        "description": "Custom SMS message templates",
        "collections": [
            {"display_name": "SMS Template", "collection_name": "okta_template_sms", "id_field": "sms_id"},
        ],
    },
    "network_zones": {
        "display_name": "Network Zones",
        "category": "Security",
        "is_active": False,
        "description": "IP and geographic network zone definitions",
        "collections": [
            {"display_name": "Network Zone", "collection_name": "okta_network_zone", "id_field": "network_id"},
        ],
    },
    "entity_risk_policy": {
        "display_name": "Entity Risk Policy",
        "category": "Policies",
        "is_active": False,
        "description": "Entity risk policies and rules",
        "collections": [
            {"display_name": "Entity Risk Policy",      "collection_name": "okta_entity_risk_policy",      "id_field": "policy_id"},
            {"display_name": "Entity Risk Policy Rule", "collection_name": "okta_entity_risk_policy_rule", "id_field": "policy_rule_id"},
        ],
    },
}
