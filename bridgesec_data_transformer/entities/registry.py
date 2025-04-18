from entities.okta_entities.auth_server.views.auth_server_base_viewset import (
    BaseAuthServerViewSet,
)
from entities.okta_entities.auth_server.views.auth_server_claim_viewset import (
    AuthorizationServerClaimViewSet,
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
from entities.okta_entities.authenticator.views.authenticator_viewset import (
    AuthenticatorViewSet,
)
from entities.okta_entities.behavior.views.behavior_viewset import BehaviorViewSet
from entities.okta_entities.brands.views.brand_viewset import BrandEntityViewSet
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
from entities.okta_entities.event_hook.views.event_hook_viewset import EventHookViewSet
from entities.okta_entities.groups.views.group_base_viewset import BaseGroupViewSet
from entities.okta_entities.groups.views.group_membership_viewset import (
    GroupMembershipViewSet,
)
from entities.okta_entities.groups.views.group_role_viewset import GroupRoleViewSet
from entities.okta_entities.groups.views.group_rule_viewset import GroupRuleViewSet
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
from entities.okta_entities.inline_hooks.views.inline_hook_viewset import (
    InlineHookEntityViewSet,
)
from entities.okta_entities.network_zone.views.network_zone_viewset import (
    NetworkZoneViewSet,
)
from entities.okta_entities.org.views.org_viewset import OrgViewSet
from entities.okta_entities.sms_templates.views.sms_template_viewset import (
    SmsTemplateViewSet,
)
from entities.okta_entities.threat_insights.views.threat_insight_viewset import (
    ThreatInsightViewSet,
)
from entities.okta_entities.trusted_origins.views.trusted_origin_viewset import (
    TrustedOriginViewSet,
)
from entities.okta_entities.users.views.user_base_viewset import BaseUserViewSet
from entities.okta_entities.users.views.user_factor_viewset import UserFactorViewSet
from entities.okta_entities.users.views.user_type_viewset import UserTypeViewSet
from entities.okta_entities.users.views.user_viewset import UserViewSet

# from entities.okta_entities.groups.views.group_owner_viewset import GroupOwnerViewSet

# Dictionary to register all entity viewsets
ENTITY_VIEWSETS = {
    "users": BaseUserViewSet,
    # "domains": DomainEntityViewSet,
    "identity_providers": BaseIdentityProviderViewSet,
    # "roles": AdministrativeRoleEntityViewSet,
    "behavior": BehaviorViewSet, 
    "orgs": OrgViewSet,
    "authenticators": AuthenticatorViewSet,
    "groups": BaseGroupViewSet,
    "brands": BrandEntityViewSet,
    "sms_templates": SmsTemplateViewSet,
    "threat_insights": ThreatInsightViewSet,
    "network_zones": NetworkZoneViewSet,
    "inline_hooks": InlineHookEntityViewSet,
    "event_hooks": EventHookViewSet,
    "auth_server": BaseAuthServerViewSet,
    "trusted_origins": TrustedOriginViewSet,
    "device_assurance_policy": BaseDeviceAssurancePolicyViewSet
}

GROUP_ENTITY_VIEWSETS = {
    "groups": GroupEntityViewSet,
    "group_memberships": GroupMembershipViewSet,
    # "group_owners": GroupOwnerViewSet
    "group_roles": GroupRoleViewSet,
    "group_rules": GroupRuleViewSet
}

AUTH_SERVER_ENTITY_VIEWSETS = {
    "auth_servers": AuthorizationServerViewSet,
    "auth_server_claims": AuthorizationServerClaimViewSet,
    "auth_server_policy": AuthorizationServerPolicyViewSet,
    "auth_server_policy_rules": AuthorizationServerPolicyRuleViewSet,
    "auth_server_scopes": AuthorizationServerScopeViewSet,
    "auth_trusted_servers": AuthTrustedServerViewSet,
}

USER_ENTITY_VIEWSETS = {
    "users": UserViewSet,
    "user_types": UserTypeViewSet,
    # "user_factors": UserFactorViewSet
}

IDENTITY_PROVIDER_ENTITY_VIEWSETS = {
    "okta_idp_oidc": IdentityProviderOIDCViewSet,
    # "okta_idp_saml": IdentityProviderSAMLViewSet,
}

DEVICE_ASSURANCE_POLICY_ENTITY_VIEWSETS = {
    "okta_policy_device_assurance_android": DeviceAndroidViewSet,
    "okta_policy_device_assurance_macos": DeviceMacOSViewSet,
    "okta_policy_device_assurance_windows": DeviceWindowsViewSet,
    "okta_policy_device_assurance_ios": DeviceIOSViewSet
}