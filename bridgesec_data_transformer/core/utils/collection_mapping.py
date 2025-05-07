RESOURCE_COLLECTION_MAP = {
    "user": ["okta_user"],
    "user_type": ["okta_user_type"],
    "group_roles": ["okta_group_role"],
    "group_rules": ["okta_group_rule"],
    "group_memberships": ["okta_group_memberships"],
    "group": ["okta_group"],
    "authorization_server": [
        "okta_auth_server", "okta_auth_server_claim", "okta_auth_server_policy",
        "okta_auth_server_policy_rule", "okta_auth_server_scope"
    ], # Add more logical groupings as needed
    "authorization_server_policy": ["okta_auth_server_policy", "okta_auth_server_policy_rule"],
    "identity_providers": [
        "okta_idp_oidc", "okta_idp_saml", "okta_idp_social"
    ],
    "policy_mfa": ["okta_policy_mfa", "okta_policy_rule_mfa"],
    "policy_password": ["okta_policy_password", "okta_policy_rule_password"],
    "policy_profile_enrollment": ["okta_policy_profile_enrollment", "okta_policy_rule_profile_enrollment"],
    "policy_sign_on": ["okta_policy_sign_on", "okta_policy_rule_sign_on"],
}