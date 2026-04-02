"""
Serializer Registry
Maps entity names (from RESOURCE_COLLECTION_MAP) to their corresponding serializer classes.
Used for validating data before storing in MongoDB.
"""
from entities.okta_entities.brands.brand_serializers import EmailDomainSerializer
from entities.okta_entities.users.user_serializers import UserTypeSerializer,UserSerializer,UserSchemaPropertySerializer,UserAdminRolesSerializer,UserGroupMembershipsSerializer,UserBaseSchemaPropertySerializer
from entities.okta_entities.administrators.administrators_serializers import \
    AdminRoleCustomSerializer
from entities.okta_entities.brands.brand_serializers import OktaThemeSerializer 
from entities.okta_entities.authenticator.authenticator_serializers import OktaFactorSerializer
# Import all serializer classes
from entities.okta_entities.apps.apps_serializers import (
    AppAccessPolicyAssignmentSerializer, AppAutoLoginSerializer,
    AppBasicAuthSerializer, AppBookMarkSerializer,
    AppGroupAssignmentSerializer, AppGroupAssignmentsSerializer,
    AppOauthApiScopeSerializer, AppOauthPostRedirectUriSerializer,
    AppOauthRedirectUriSerializer, AppOAuthRoleAssignmentSerializer,
    AppOauthSerializer, AppPolicySignOnRuleSerializer,
    AppPolicySignOnSerializer, AppSAMLSerializer, AppSAMLSettingsSerializer,
    AppSecurePasswordStoreSerializer, AppSharedCredentialsSerializer,
    AppSwaSerializer, AppThreeFieldSerializer,
    AppUserBaseSchemaPropertySerializer, AppUserSchemaPropertySerializer,
    AppUserSerializer)
from entities.okta_entities.auth_server.auth_server_serializers import \
    AuthorizationServerSerializer
from entities.okta_entities.behavior.behavior_serializer import \
    BehaviorSerializer
from entities.okta_entities.brands.brand_serializers import BrandSerializer
from entities.okta_entities.device_assurance_policies.device_assurance_policy_serializers import (
    DeviceAndroidSerializer, DeviceIosSerializer, DeviceMacOSSerializer,
    DeviceWindowsSerializer)
from entities.okta_entities.email.email_serializers import \
    EmailSmtpServerSerializer
from entities.okta_entities.entitlements.entitlement_serializers import (
    EntitlementBundleSerializer, PrincipalEntitlementSerializer, EntitlementSerializer)
from entities.okta_entities.event_hook.event_hook_serializer import \
    EventHookSerializer
from entities.okta_entities.groups.group_serializers import (
    GroupMemberSerializer, GroupRoleSerializer, GroupRuleSerializer,
    GroupSchemaPropertySerializer, GroupSerializer)
from entities.okta_entities.identity_providers.identity_provider_serializers import (
    IdentityProviderOIDCSerializer, IdentityProviderSAMLSerializer,
    IdentityProviderSocialSerializer)
from entities.okta_entities.inline_hooks.inline_hook_serializer import \
    InlineHookSerializer
from entities.okta_entities.network_zone.network_zone_serializer import \
    NetworkZoneSerializer
from entities.okta_entities.org.org_serializers import OrgSerializer
from entities.okta_entities.policies.policy_serializers import (
    PolicyMFASerializer, PolicyPasswordSerializer,PolicyRuleMFASerializer,
    PolicyProfileEnrollmentSerializer, PolicySignOnSerializer,PolicyRulePasswordSerializer,PolicyRuleSignOnSerializer,PolicyRuleProfileEnrollmentSerializer)
from entities.okta_entities.rate_limits.rate_limit_serializer import (
    PrincipalRateLimitSerializer, RateLimitAdminNotificationSerializer,
    RateLimitWarningThresholdSerializer)
from entities.okta_entities.requests.request_condition_serializers import (
    RequestConditionSerializer, RequestSequenceSerializer,
    RequestSettingsSerializer)
from entities.okta_entities.sms_templates.sms_template_serializers import \
    SmsTemplateSerializer
from entities.okta_entities.threat_insights.threat_insight_serializer import \
    ThreatInsightSerializer
from entities.okta_entities.trusted_origins.trusted_origin_serializers import \
    TrustedOriginSerializer

# Serializer Registry - Maps entity display names to their serializer classes
SERIALIZER_REGISTRY = {
    # Applications
    "App Oauth": AppOauthSerializer,
    "App Saml": AppSAMLSerializer,
    "App Group Assignments": AppGroupAssignmentsSerializer,
    "App Access Policy Assignment": AppAccessPolicyAssignmentSerializer,
    "App Signon Policy": AppPolicySignOnSerializer,
    "App Group Assignment": AppGroupAssignmentSerializer,
    "App Bookmark": AppBookMarkSerializer,
    "App Auto Login": AppAutoLoginSerializer,
    "App Three Field": AppThreeFieldSerializer,
    "App Secure Password Store": AppSecurePasswordStoreSerializer,
    "App User Schema Property": AppUserSchemaPropertySerializer,
    "App User Base Schema Property": AppUserBaseSchemaPropertySerializer,
    "App Basic Auth": AppBasicAuthSerializer,
    "App SWA": AppSwaSerializer,
    "App User": AppUserSerializer,
    "App Signon Policy Rule":AppPolicySignOnRuleSerializer,
    "App Shared Credentials":AppSharedCredentialsSerializer,
    "App Saml Settings":AppSAMLSettingsSerializer,
    "App Oauth Role Assignment":AppOAuthRoleAssignmentSerializer,
    "App Oauth Post Logout Redirect Uri":AppOauthPostRedirectUriSerializer,
    "App Oauth Redirect Uri":AppOauthRedirectUriSerializer,
    "App User Schema Property":AppUserSchemaPropertySerializer,
    "App Oauth Api Scope":AppOauthApiScopeSerializer,

    
    "Users":UserSerializer,
    "User Schema Properties":UserSchemaPropertySerializer,
    "User Group Memberships":UserGroupMembershipsSerializer,
    "User Base Schema Properties":UserBaseSchemaPropertySerializer,
    "User Admin Roles":UserAdminRolesSerializer,

    "User Types":UserTypeSerializer,

    # Groups
    "Groups": GroupSerializer,
    "Group Schema Property": GroupSchemaPropertySerializer,
    "Group Rules": GroupRuleSerializer,
    "Group Roles": GroupRoleSerializer,
    "Group Memberships": GroupMemberSerializer,

    # Brands
    "Brands": BrandSerializer,
    "Email Domain":EmailDomainSerializer,

    # Device Assurance Policies
    "Policy Device Assurance Android": DeviceAndroidSerializer,
    "Policy Device Assurance IOS": DeviceIosSerializer,
    "Policy Device Assurance Macos": DeviceMacOSSerializer,
    "Policy Device Assurance Windows": DeviceWindowsSerializer,

    # Email
    "Email SMTP Server": EmailSmtpServerSerializer,

    "Themes": OktaThemeSerializer,

    # Rate Limits
    "Principal Rate Limit": PrincipalRateLimitSerializer,
    "Rate Limit Admin Notification": RateLimitAdminNotificationSerializer,
    "Rate Limit Warning Threshold Percentage": RateLimitWarningThresholdSerializer,

    # Entitlements
    "Entitlement Bundle": EntitlementBundleSerializer,
    "Principal Entitlement": PrincipalEntitlementSerializer,
    "Entitlements":EntitlementSerializer,

    # Requests
    "Request Condition": RequestConditionSerializer,
    "Request Sequence": RequestSequenceSerializer,
    "Request Settings": RequestSettingsSerializer,

    # SMS Templates
    "Sms Template": SmsTemplateSerializer,

    # Organization Security
    "Organization Security": OrgSerializer,

    # Threat Insights
    "Threat Insights": ThreatInsightSerializer,

    # Authorization Servers
    "Auth Server": AuthorizationServerSerializer,

    # Identity Providers
    "IDP OIDC": IdentityProviderOIDCSerializer,
    "IDP SAML": IdentityProviderSAMLSerializer,
    "IDP SOCIAL": IdentityProviderSocialSerializer,

    # Network Zone
    "Network Zone": NetworkZoneSerializer,

    # Behavior
    "Behavior": BehaviorSerializer,

    # Administrator Roles
    "Admin Role Custom": AdminRoleCustomSerializer,

    # Trusted Origins
    "Trusted Origin": TrustedOriginSerializer,

    # Inline Hooks
    "Inline Hook": InlineHookSerializer,

    # Event Hooks
    "Event_Hook": EventHookSerializer,

    # Policies
    "Policy MFA": PolicyMFASerializer,
    "Policy Rule Mfa":PolicyRuleMFASerializer,
    "Policy Password": PolicyPasswordSerializer,
    "Policy Profile Enrollment": PolicyProfileEnrollmentSerializer,
    "Policy Sign On": PolicySignOnSerializer,
    "Policy Rule Password":PolicyRulePasswordSerializer,
    "Policy Rule Profile Enrollment":PolicyRuleProfileEnrollmentSerializer,

    "Factor":OktaFactorSerializer,
}
