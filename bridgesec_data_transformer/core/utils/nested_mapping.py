"""
Configuration mappings for entities with nested data structures.

This module contains all the mappings needed to handle entities that have
nested arrays (like Policy MFA with policy_rules, Auth Server with scopes, etc.)
"""

# Entities that have nested data builders
ENTITIES_WITH_BUILDERS = [
    "Auth Server",
    "Policy MFA",
    "App Signon Policy",
    "Policy Password",
    "Policy Profile Enrollment",
    "Policy Sign On",
    "Admin Role Custom"
]

# Mapping of nested field names to their collection names for entities with builders
NESTED_FIELD_COLLECTIONS = {
    "Auth Server": {
        "authorization_server_scopes": "okta_auth_server_scope",
        "authorization_server_claims": "okta_auth_server_claim",
        "authorization_server_accessPolicies": "okta_auth_server_policy",
        "authorization_server_accessPoliciesRules": "okta_auth_server_policy_rule",
        "authorization_server_trusted_servers": "okta_trusted_server",
    },
    "Policy MFA": {
        "policy_rules": "okta_policy_rule_mfa",
    },
    "App Signon Policy": {
        "policy_rules": "okta_app_signon_policy_rule",
    },
    "Policy Password": {
        "policy_password_rules": "okta_policy_rule_password",
    },
    "Policy Profile Enrollment": {
        "policy_enrollment_rules": "okta_policy_rule_profile_enrollment",
        "policy_enrollment_apps": "okta_policy_profile_enrollment_apps",
    },
    "Policy Sign On": {
        "policy_signon_rules": "okta_policy_rule_sign_on",
    },
    "Admin Role Custom": {
        "resource_sets": "okta_resource_set",
    },
}

# Comprehensive mapping of nested fields with both parent ID and child item ID
NESTED_FIELD_ID_MAPPING = {
    "authorization_server_scopes": {
        "parent_id_field": "auth_server_id",
        "child_id_field": "scope_id"
    },
    "authorization_server_claims": {
        "parent_id_field": "auth_server_id",
        "child_id_field": "claim_id"
    },
    "authorization_server_accessPolicies": {
        "parent_id_field": "auth_server_id",
        "child_id_field": "policy_id"
    },
    "authorization_server_accessPoliciesRules": {
        "parent_id_field": "auth_server_id",
        "child_id_field": "policy_rule_id"
    },
    "authorization_server_trusted_servers": {
        "parent_id_field": "auth_server_id",
        "child_id_field": "auth_server_id"
    },
    "policy_rules": {
        "parent_id_field": "policy_id",
        "child_id_field": "policy_rule_id"
    },
    "policy_password_rules": {
        "parent_id_field": "policy_id",
        "child_id_field": "policy_id"
    },
    "policy_signon_rules": {
        "parent_id_field": "policy_id",
        "child_id_field": "policy_signon_rule_id"
    },
    "policy_enrollment_rules": {
        "parent_id_field": "policy_id",
        "child_id_field": "policy_rule_id"
    },
    "policy_enrollment_apps": {
        "parent_id_field": "policy_id",
        "child_id_field": "app_id"
    },
    "resource_sets": {
        "parent_id_field": "role_id",
        "child_id_field": "resource_set_id"
    },
    "policy_apps": {
        "parent_id_field": "app_policy_id",
        "child_id_field": "policy_id"
    },
}

