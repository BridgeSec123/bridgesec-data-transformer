"""
Entity Model Registry
Maps entity names (from RESOURCE_COLLECTION_MAP) to their corresponding mongoengine model classes.
Used for dynamic schema extraction and entity operations.
"""

# Import all model classes
from entities.okta_entities.brands.brand_models import EmailDomain
from entities.okta_entities.users.user_models import User,UserSchemaProperty,UserAdminRoles,UserBaseSchemaProperty,UserGroupMemberships,UserType
from entities.okta_entities.auth_server.auth_server_models import AuthorizationServer
from entities.okta_entities.policies.policy_models import (
    PolicyMFA, PolicyPassword, PolicyProfileEnrollment, PolicySignOn,PolicyRuleMFA,PolicyRulePassword,PolicyRuleProfileEnrollment,PolicyRuleSignOn
)
from entities.okta_entities.authenticator.authenticator_models import OktaFactor
from entities.okta_entities.brands.brand_models import OktaTheme
from entities.okta_entities.administrators.administrators_models import AdminRoleCustom
from entities.okta_entities.apps.apps_models import (
    AppOauth, AppSAML, AppGroupAssignments, AppAccessPolicyAssignment,
    AppSharedCredentials,AppSAMLSettings,AppOauthPostRedirectUri,AppOauthRedirectUri,
    AppPolicySignOn, AppGroupAssignment, AppBookMark, AppAutoLogin,
    AppThreeField, AppSecurePasswordStore, AppUserSchemaProperty,
    AppUserBaseSchemaProperty, AppBasicAuth, AppSwa, AppUser,AppPolicySignOnRule,AppOAuthRoleAssignment
)
from entities.okta_entities.groups.group_models import (
    Group, GroupSchemaProperty, GroupRule, GroupRole, GroupMember
)
from entities.okta_entities.brands.brand_models import Brand
from entities.okta_entities.device_assurance_policies.device_assurance_policy_models import (
    DeviceAndroid, DeviceIos, DeviceMacOS, DeviceWindows
)
from entities.okta_entities.sms_templates.sms_template_models import SmsTemplate
from entities.okta_entities.org.org_models import Org
from entities.okta_entities.threat_insights.threat_insight_models import ThreatInsight
from entities.okta_entities.identity_providers.identity_provider_models import (
    IdentityProviderOIDC, IdentityProviderSAML, IdentityProviderSocial
)
from entities.okta_entities.network_zone.network_zone_models import NetworkZone
from entities.okta_entities.behavior.behavior_models import Behavior
from entities.okta_entities.trusted_origins.trusted_origin_models import TrustedOrigin
from entities.okta_entities.inline_hooks.inline_hook_models import InlineHook
from entities.okta_entities.event_hook.event_hook_models import EventHook
from entities.okta_entities.email.email_models import EmailSmtpServer
from entities.okta_entities.entitlements.entitlement_models import EntitlementBundle, PrincipalEntitlement,Entitlement
from entities.okta_entities.requests.request_condition_models import RequestCondition, RequestSequence, RequestSettings
from entities.okta_entities.rate_limits.rate_limit_models import PrincipalRateLimit, RateLimitAdminNotification, RateLimitWarningThreshold
# from entities.okta_entities.link.link_models import LinkDefinition


# Model Registry - Maps entity display names to their model classes
MODEL_REGISTRY = {
    # Authorization Servers
    "Auth Server": AuthorizationServer,

    # Policies
    "Policy MFA": PolicyMFA,
    "Policy Rule Mfa":PolicyRuleMFA,
    "Policy Password": PolicyPassword,
    "Policy Profile Enrollment": PolicyProfileEnrollment,
    "Policy Sign On": PolicySignOn,

    # Administrator Roles
    "Admin Role Custom": AdminRoleCustom,

    # Applications
    "App Oauth": AppOauth,
    "App Saml": AppSAML,
    "App Saml Settings":AppSAMLSettings,
    "App Group Assignments": AppGroupAssignments,
    "App Access Policy Assignment": AppAccessPolicyAssignment,
    "App Signon Policy": AppPolicySignOn,
    "App Group Assignment": AppGroupAssignment,
    "App Bookmark": AppBookMark,
    "App Auto Login": AppAutoLogin,
    "App Three Field": AppThreeField,
    "App Secure Password Store": AppSecurePasswordStore,
    "App User Schema Property": AppUserSchemaProperty,
    "App User Base Schema Property": AppUserBaseSchemaProperty,
    "App Basic Auth": AppBasicAuth,
    "App SWA": AppSwa,
    "App User": AppUser,
    "App Signon Policy Rule":AppPolicySignOnRule,
    "App Shared Credentials":AppSharedCredentials,
    "App Oauth Role Assignment":AppOAuthRoleAssignment,
    "App Oauth Post Logout Redirect Uri":AppOauthPostRedirectUri,
    "App Oauth Redirect Uri":AppOauthRedirectUri,
    "App User Schema Property":AppUserSchemaProperty,

    # Groups
    "Groups": Group,
    "Group Schema Property": GroupSchemaProperty,
    "Group Rules": GroupRule,
    "Group Roles": GroupRole,
    "Group Memberships": GroupMember,

    # Brands
    "Brands": Brand,
    "Email Domain":EmailDomain,

    # Device Assurance Policies
    "Policy Device Assurance Android": DeviceAndroid,
    "Policy Device Assurance IOS": DeviceIos,
    "Policy Device Assurance Macos": DeviceMacOS,
    "Policy Device Assurance Windows": DeviceWindows,
    "Policy Rule Password":PolicyRulePassword,
    "Policy Rule Profile Enrollment":PolicyProfileEnrollment,
    # Email
    "Email SMTP Server": EmailSmtpServer,

    "Themes":OktaTheme,

    # Rate Limits
    "Principal Rate Limit": PrincipalRateLimit,
    "Rate Limit Admin Notification": RateLimitAdminNotification,
    "Rate Limit Warning Threshold Percentage": RateLimitWarningThreshold,

    # Entitlements
    "Entitlement Bundle": EntitlementBundle,
    "Principal Entitlement": PrincipalEntitlement,
    "Entitlements":Entitlement,

    # Requests
    "Request Condition": RequestCondition,
    "Request Sequence": RequestSequence,
    "Request Settings": RequestSettings,

    # SMS Templates
    "Sms Template": SmsTemplate,

    # Organization Security
    "Organization Security": Org,

    # Threat Insights
    "Threat Insights": ThreatInsight,

    # Identity Providers
    "IDP OIDC": IdentityProviderOIDC,
    "IDP SAML": IdentityProviderSAML,
    "IDP SOCIAL": IdentityProviderSocial,

    # Network Zone
    "Network Zone": NetworkZone,

    # Behavior
    "Behavior": Behavior,

    # Trusted Origins
    "Trusted Origin": TrustedOrigin,

    # Inline Hooks
    "Inline Hook": InlineHook,

    # Event Hooks
    "Event_Hook": EventHook,

    "Users":User,
    "User Schema Properties":UserSchemaProperty,
    "User Group Memberships":UserGroupMemberships,
    "User Base Schema Properties":UserBaseSchemaProperty,
    "User Admin Roles":UserAdminRoles,
    "User Types":UserType,

    "Factor":OktaFactor,


    # Link
    # "Link Definition": LinkDefinition,
}
