"""
OkTfModules mapping dicts, copied into bridgesec-data-transformer so the Supabase
populate service (entities/services/SupabasePopulateService.py) has a single
entrypoint for all mappings across both repos.

These are the source of truth for the OkTf-only mappings until the Phase-2
read-side cutover, after which OkTfModules reads them back from Supabase.

Copied verbatim from
  OkTfModules/bridgesec_data_transformer/terraform_workflow/scripts/
    - entity_mapping.py          -> ENTITY_FIELD_MAPPING, NESTED_ENTITY_KEYS
    - collection_state_mapping.py -> COLLECTION_STATE_MAP, GROUPED_ENTITIES
    - terraform_target_mapping.py -> NESTED_ENTITY_CONFIG
    - utils.py                    -> ENTITY_DEPENDENCY_MAPPING

Keep in sync with those files until OkTf switches to reading Supabase.
"""

# ---------------------------------------------------------------------------
# entity_type -> JSON wrapper key   (-> terraform_registry.wrapper_key)
# from scripts/entity_mapping.py
# ---------------------------------------------------------------------------
ENTITY_FIELD_MAPPING = {
    "okta_app_oauth": "app_oauth_list",
    "okta_user": "users_list",
    "okta_app_group_assignments": "app_group_assignments_list",
    "okta_app_basic_auth": "app_basic_list",
    "okta_app_auto_login": "app_auto_login_list",
    "okta_app_group_assignment": "app_group_assignment_list",
    "okta_app_bookmark": "app_bookmark_list",
    "okta_app_signon_policy": "app_signon_policy_list",
    "okta_app_swa": "app_swa_list",
    "okta_app_three_field": "app_three_field_list",
    "okta_app_saml": "app_saml_list",
    "okta_app_shared_credentials": "app_shared_credentials_list",
    "okta_app_oauth_role_assignment": "app_oauth_role_assignments",
    "okta_app_oauth_api_scope": "app_oauth_api_scope_list",
    "okta_app_access_policy_assignment": "app_access_policy_assignment",
    "okta_user_schema_property": "user_schema_properties",
    "okta_user_base_schema_property": "user_base_schema_properties",
    "okta_user_type": "user_type",
    "okta_group": "groups_list",
    "okta_group_role": "group_roles_list",
    "okta_group_rule": "group_rules_list",
    "okta_group_memberships": "group_memberships_list",
    "okta_policy_sign_on": "global_signon_policies",
    "okta_group_schema_property": "group_schema_property_list",
    "okta_authenticator": "authenticators_list",
    "okta_policy_mfa": "authenticator_enroll_policies_list",
    "okta_policy_profile_enrollment": "profile_enrollment_list",
    "okta_network_zone": "network_zones_list",
    "okta_inline_hook": "inline_hooks",
    "okta_policy_password": "policy_password_list",
    "okta_app_user_base_schema_property": "app_user_base_schema_property_list",
    "okta_policy_rule_idp_discovery": "idp_discovery_list",
    "okta_idp_oidc": "idp_oidc_list",
    "okta_idp_saml": "idp_saml_list",
    "okta_idp_social": "idp_social_list",
    "okta_auth_server": "authorization_server_list",
    "okta_behavior": "behavior_list",
    "okta_user_group_memberships": "okta_user_group_memberships",
    "okta_org_configuration": "org_configuration_map",
    "okta_brand": "brand_list",
    "okta_theme": "theme_list",
    "okta_trusted_origin": "trusted_origins_map",
    "okta_event_hook": "event_hooks_list",
    "okta_policy_device_assurance_android": "device_assurance_android",
    "okta_policy_device_assurance_ios": "device_assurance_ios",
    "okta_policy_device_assurance_windows": "device_assurance_windows_list",
    "okta_policy_device_assurance_macos": "device_assurance_macos",
    "okta_app_secure_password_store": "app_secure_password_store_list",
    "okta_policy_device_assurance_chromeos": "device_assurance_chromeos",
    "okta_app_user": "app_user_list",
    "okta_apps_oauth_api_scope": "apps_oauth_api_scope_list",
    "okta_app_oauth_redirect_uri": "apps_oauth_redirect_uri_list",
    "okta_app_oauth_post_logout_redirect_uri": "apps_oauth_post_redirect_uri_list",
    "okta_admin_role_custom": "admin_role_custom_list",
    "okta_email_domain": "email_domain_list",
    "okta_template_sms": "sms_templates_list",
    "okta_threat_insight_settings": "threat_insight_list",
    "okta_link_definition": "link_definition_list",
    "okta_user_admin_roles": "user_admin_roles",
    "okta_email_smtp_server": "email_smtp_server_list",
    "okta_principal_rate_limits": "principal_rate_limits_list",
    "okta_review": "review_list",
    "okta_principal_entitlements": "principal_entitlements_list",
    "okta_request_condition": "request_condition_list",
    "okta_request_sequence": "request_sequence_list",
    "okta_request_v2": "request_v2_list",
    "okta_catalog_entry_default": "catalog_entry_default_list",
    "okta_end_user_my_requests": "end_user_my_requests_list",
    "okta_entitlement_bundle": "entitlement_bundle_list",
    "okta_entitlement": "entitlement_list",
    "okta_request": "request_list",
    "okta_request_settings": "request_settings_list",
    "okta_rate_limit_admin_notification_settings": "rate_limit_admin_notification_map",
    "okta_rate_limit_warning_threshold_percentage": "rate_limit_warning_threshold_map",
    "okta_domain": "domain_list",
    "okta_hook_key": "hook_key_list",
    "okta_api_token": "api_token_list",
    "okta_app_token": "app_token_list",
    "okta_app_connection": "app_connection_list",
    "okta_push_provider": "push_provider_list",
    "okta_api_service_integration": "api_service_integration_list",
    "okta_ui_schema": "ui_schema_list",
    "okta_agent_pools": "agent_pools_list",
    "okta_app_federated_claim": "app_federated_claim_list",
    "okta_user_risk": "user_risk_list",
    "okta_entity_risk_policy_rule": "entity_risk_policy_rule_list",
    "okta_set_usage_as_exempt_list": "set_usage_as_exempt_list",
}

# ---------------------------------------------------------------------------
# Nested unique keys: {parent_wrapper_key: {nested_array_field: unique_key}}
#   (-> nested_entity_mapping.child_unique_key)
# from scripts/entity_mapping.py
# ---------------------------------------------------------------------------
NESTED_ENTITY_KEYS = {
    "authorization_server_list": {
        "authorization_server_scopes": "scope_id",
        "authorization_server_claims": "claim_id",
        "authorization_server_accessPolicies": "policy_id",
        "authorization_server_accessPoliciesRules": "policy_rule_id",
        "authorization_server_trusted_servers": "auth_server_id",
    },
    "authenticator_enroll_policies_list": {
        "policy_rules": "policy_rule_id",
    },
    "app_signon_policy_list": {
        "policy_rules": "policy_rule_id",
    },
    "global_signon_policies": {
        "policy_signon_rules": "policy_signon_rule_id",
    },
    "policy_password_list": {
        "policy_password_rules": "policy_password_id",
    },
    "profile_enrollment_list": {
        "policy_enrollment_rules": "policy_profile_rule_id",
    },
}

# ---------------------------------------------------------------------------
# entity_type -> Terraform state file path   (-> terraform_registry.state_file_path)
# from scripts/collection_state_mapping.py
# ---------------------------------------------------------------------------
COLLECTION_STATE_MAP = {
    # App Modules
    "okta_app_oauth": "deployments/app_oauth/terraform.tfstate",
    "okta_app_group_assignment": "deployments/app_group_assignment/terraform.tfstate",
    "okta_app_saml": "deployments/app_saml/terraform.tfstate",
    "okta_app_shared_credentials": "deployments/app_shared_credentials/terraform.tfstate",
    "okta_app_auto_login": "deployments/app_auto_login/terraform.tfstate",
    "okta_app_bookmark": "deployments/app_bookmark/terraform.tfstate",
    "okta_app_user": "deployments/app_user/terraform.tfstate",
    "okta_app_oauth_api_scope": "deployments/app_oauth_api_scope/terraform.tfstate",
    "okta_app_oauth_redirect_uri": "deployments/app_oauth_redirect_uri/terraform.tfstate",
    "okta_app_oauth_post_redirect_uri": "deployments/app_oauth_post_redirect_uri/terraform.tfstate",
    "okta_app_three_field": "deployments/app_three_field/terraform.tfstate",
    "okta_app_secure_password_store": "deployments/app_secure_password_store/terraform.tfstate",
    "okta_app_user_base_schema_property": "deployments/app_user_base_schema_property_list/terraform.tfstate",
    "okta_app_user_schema_property": "deployments/app_use_schema_property_list/terraform.tfstate",
    "okta_app_group_assignments": "deployments/app_group_assignments/terraform.tfstate",
    "okta_app_access_policy_assignment": "deployments/app_access_policy_assignment/terraform.tfstate",
    "okta_app_signon_policy": "deployments/app_signon_policies1/terraform.tfstate",
    "okta_app_basic_auth": "deployments/app_basic_auth/terraform.tfstate",
    "okta_app_swa": "deployments/app_swa/terraform.tfstate",
    # User & Group Modules
    "okta_user": "deployments/users/terraform.tfstate",
    "okta_user_type": "deployments/user_types/terraform.tfstate",
    "okta_user_schema_property": "deployments/user_schema_property/terraform.tfstate",
    "okta_user_base_schema_property": "deployments/user_base_schema_property/terraform.tfstate",
    "okta_user_group_memberships": "deployments/user_group_memberships/terraform.tfstate",
    "okta_user_admin_roles": "deployments/user_admin_roles/terraform.tfstate",
    "okta_group": "deployments/groups_1/terraform.tfstate",
    "okta_group_memberships": "deployments/group_memberships/terraform.tfstate",
    "okta_group_rule": "deployments/group_rules/terraform.tfstate",
    "okta_group_role": "deployments/group_roles/terraform.tfstate",
    "okta_group_schema_property": "deployments/group_schema_property/terraform.tfstate",
    "okta_admin_role_custom": "deployments/admin_role_custom/terraform.tfstate",
    # Policy Modules
    "okta_global_signon_policies": "deployments/global_signon_policies/terraform.tfstate",
    "okta_policy_signon": "deployments/global_signon_policies/terraform.tfstate",
    "okta_policy_sign_on": "deployments/global_signon_policies/terraform.tfstate",
    "okta_password_policy": "deployments/password_policy/terraform.tfstate",
    "okta_policy_password": "deployments/password_policy/terraform.tfstate",
    "okta_policy_mfa": "deployments/mfa_policy/terraform.tfstate",
    "okta_policy_rule_mfa": "deployments/mfa_policy/terraform.tfstate",
    "okta_policy_rule_password": "deployments/password_policy/terraform.tfstate",
    "okta_authenticator_enroll_policies": "deployments/authenticator_enroll_policies/terraform.tfstate",
    "okta_policy_device_assurance_windows": "deployments/device_assurance_windows/terraform.tfstate",
    "okta_policy_device_assurance_macos": "deployments/device_assurance_macos/terraform.tfstate",
    "okta_policy_device_assurance_ios": "deployments/device_assurance_ios/terraform.tfstate",
    "okta_policy_device_assurance_android": "deployments/device_assurance_android/terraform.tfstate",
    "okta_policy_profile_enrollment": "deployments/policy_profile_enrollment/terraform.tfstate",
    # Rule Collections
    "okta_app_signon_policy_rule": "deployments/app_signon_policies1/terraform.tfstate",
    "okta_policy_rule_signon": "deployments/global_signon_policies/terraform.tfstate",
    "okta_policy_rule_sign_on": "deployments/global_signon_policies/terraform.tfstate",
    # Identity Provider Modules
    "okta_idp_oidc": "deployments/idp_oidc/terraform.tfstate",
    "okta_idp_social": "deployments/idp_social/terraform.tfstate",
    "okta_idp_saml": "deployments/idp_saml/terraform.tfstate",
    "okta_idp_discovery": "deployments/idp_discovery/terraform.tfstate",
    # Other Modules
    "okta_auth_server": "deployments/auth_server/terraform.tfstate",
    "okta_behavior": "deployments/behavior/terraform.tfstate",
    "okta_brand": "deployments/brand/terraform.tfstate",
    "okta_email_domain": "deployments/email_domain/terraform.tfstate",
    "okta_theme": "deployments/theme/terraform.tfstate",
    "okta_inline_hook": "deployments/inline_hooks/terraform.tfstate",
    "okta_template_sms": "deployments/template_sms/terraform.tfstate",
    "okta_trusted_origin": "deployments/trusted_origin/terraform.tfstate",
    "okta_org_configuration": "deployments/org_configuration/terraform.tfstate",
    "okta_threat_insight_settings": "deployments/threat_insight/terraform.tfstate",
    "okta_link_definition": "deployments/link_definition/terraform.tfstate",
    "okta_event_hook": "deployments/event_hook/terraform.tfstate",
    "okta_network_zone": "deployments/network_zone/terraform.tfstate",
    "okta_email_smtp_server": "deployments/email_smtp_server/terraform.tfstate",
    "okta_principal_rate_limits": "deployments/principal_rate_limits/terraform.tfstate",
    "okta_authenticator": "deployments/authenticators/terraform.tfstate",
    "okta_review": "deployments/review/terraform.tfstate",
    "okta_principal_entitlements": "deployments/principal_entitlements/terraform.tfstate",
    "okta_request_condition": "deployments/request_condition/terraform.tfstate",
    "okta_request_sequence": "deployments/request_sequence/terraform.tfstate",
    "okta_request_v2": "deployments/request_v2/terraform.tfstate",
    "okta_catalog_entry_default": "deployments/catalog_entry_default/terraform.tfstate",
    "okta_end_user_my_requests": "deployments/end_user_my_requests/terraform.tfstate",
    "okta_entitlement_bundle": "deployments/entitlement_bundle/terraform.tfstate",
    "okta_entitlement": "deployments/entitlement/terraform.tfstate",
    "okta_request": "deployments/request/terraform.tfstate",
    "okta_request_settings": "deployments/request_settings/terraform.tfstate",
    "okta_rate_limit_admin_notification_settings": "deployments/rate_limit_admin_notification/terraform.tfstate",
    "okta_rate_limit_warning_threshold_percentage": "deployments/rate_limit_warning_threshold/terraform.tfstate",
    "okta_domain": "deployments/domain/terraform.tfstate",
    "okta_hook_key": "deployments/hook_key/terraform.tfstate",
    "okta_api_token": "deployments/api_token/terraform.tfstate",
    "okta_app_token": "deployments/app_token/terraform.tfstate",
    "okta_app_connection": "deployments/app_connection/terraform.tfstate",
    "okta_push_provider": "deployments/push_provider/terraform.tfstate",
    "okta_api_service_integration": "deployments/api_service_integration/terraform.tfstate",
    "okta_ui_schema": "deployments/ui_schema/terraform.tfstate",
    "okta_agent_pools": "deployments/agent_pools/terraform.tfstate",
    "okta_app_federated_claim": "deployments/app_federated_claim/terraform.tfstate",
    "okta_user_risk": "deployments/user_risk/terraform.tfstate",
    "okta_entity_risk_policy_rule": "deployments/entity_risk_policy_rule/terraform.tfstate",
    "okta_set_usage_as_exempt_list": "deployments/set_usage_as_exempt_list/terraform.tfstate",
}

# ---------------------------------------------------------------------------
# Entities that use composite keys   (-> terraform_registry.uses_composite_key)
# from scripts/collection_state_mapping.py
# ---------------------------------------------------------------------------
GROUPED_ENTITIES = {
    "okta_app_group_assignment",
    "okta_app_access_policy_assignment",
}

# ---------------------------------------------------------------------------
# Parent/child Terraform resource addresses for nested entities
#   (-> nested_entity_mapping.parent_resource_address / child_resource_address)
# Two shapes: flat (single child) OR a "children" list (multiple children).
# from scripts/terraform_target_mapping.py
# ---------------------------------------------------------------------------
NESTED_ENTITY_CONFIG = {
    "okta_app_signon_policy": {
        "parent_id_field": "app_policy_id",
        "child_id_field": "policy_rule_id",
        "parent_resource": "module.okta_app_signon_policy.okta_app_signon_policy.app_signon_policy",
        "child_resource": "module.okta_app_signon_policy.okta_app_signon_policy_rule.app_signon_policy_rule",
    },
    "okta_policy_mfa": {
        "parent_id_field": "policy_id",
        "child_id_field": "policy_rule_id",
        "parent_resource": "module.okta_authenticators_enroll_policies.okta_policy_mfa.authenticator_enroll_policies",
        "child_resource": "module.okta_authenticators_enroll_policies.okta_policy_rule_mfa.mfa_enroll_policy_rule",
    },
    "okta_policy_sign_on": {
        "parent_id_field": "policy_signon_id",
        "child_id_field": "policy_signon_rule_id",
        "parent_resource": "module.okta_global_signon_policies.okta_policy_signon.delegate_to_app_signon_policy",
        "child_resource": "module.okta_global_signon_policies.okta_policy_rule_signon.delegate_to_app_signon_policy_rule",
    },
    "okta_policy_password": {
        "parent_id_field": "policy_id",
        "child_id_field": "policy_password_id",
        "parent_resource": "module.okta_password_policy.okta_policy_password.password_policy",
        "child_resource": "module.okta_password_policy.okta_policy_rule_password.password_policy_rule",
    },
    "okta_policy_profile_enrollment": {
        "parent_id_field": "policy_id",
        "children": [
            {
                "child_id_field": "policy_profile_rule_id",
                "child_resource": "module.okta_profile_enrollment.okta_policy_rule_profile_enrollment.profile_enrollment_rule",
            },
            {
                "child_id_field": "app_id",
                "child_resource": "module.okta_profile_enrollment.okta_policy_profile_enrollment_apps.profile_enrollment_apps",
            },
        ],
        "parent_resource": "module.okta_profile_enrollment.okta_policy_profile_enrollment.profile_enrollment",
    },
    "okta_auth_server": {
        "parent_id_field": "auth_server_id",
        "children": [
            {
                "child_id_field": "scope_id",
                "child_resource": "module.okta_auth_server.okta_auth_server_scope.azs_sfc_scopes",
            },
            {
                "child_id_field": "claim_id",
                "child_resource": "module.okta_auth_server.okta_auth_server_claim.azs_sfc_claims",
            },
            {
                "child_id_field": "policy_id",
                "child_resource": "module.okta_auth_server.okta_auth_server_policy.azs_sfc_policy",
            },
            {
                "child_id_field": "policy_rule_id",
                "child_resource": "module.okta_auth_server.okta_auth_server_policy_rule.azs_sfc_policy_rule",
            },
            {
                "child_id_field": "trusted_id",
                "child_resource": "module.okta_auth_server.okta_trusted_server.azs_sfc_trusted_server",
            },
        ],
        "parent_resource": "module.okta_auth_server.okta_auth_server.azs_sfc",
    },
}

# ---------------------------------------------------------------------------
# Cascade-delete dependency graph: parent entity -> list of child entities
#   (-> entity_dependency)
# from scripts/utils.py
# ---------------------------------------------------------------------------
ENTITY_DEPENDENCY_MAPPING = {
    # APPS MODULE
    "okta_app_oauth": [
        {"entity_name": "okta_app_group_assignment", "state_file": "deployments/app_group_assignment/terraform.tfstate", "resource_prefix": "module.okta_app_group_assignment.okta_app_group_assignment.app_group_assignment", "query_field": "app_id", "description": "Group assignments for this app"},
        {"entity_name": "okta_app_user", "state_file": "deployments/app_user/terraform.tfstate", "resource_prefix": "module.okta_app_user.okta_app_user.user", "query_field": "app_id", "description": "User assignments for this app"},
        {"entity_name": "okta_app_oauth_api_scope", "state_file": "deployments/app_oauth_api_scope/terraform.tfstate", "resource_prefix": "module.okta_app_oauth_api_scope.okta_app_oauth_api_scope.app_oauth_api_scope", "query_field": "app_id", "description": "OAuth API scopes for this app"},
        {"entity_name": "okta_app_access_policy_assignment", "state_file": "deployments/app_access_policy_assignment/terraform.tfstate", "resource_prefix": "module.okta_app_access_policy_assignment.okta_app_access_policy_assignment.assignment", "query_field": "app_id", "description": "Access policy assignments for this app"},
    ],
    "okta_app_saml": [
        {"entity_name": "okta_app_group_assignment", "state_file": "deployments/app_group_assignment/terraform.tfstate", "resource_prefix": "module.okta_app_group_assignment.okta_app_group_assignment.app_group_assignment", "query_field": "app_id", "description": "Group assignments for this app"},
        {"entity_name": "okta_app_user", "state_file": "deployments/app_user/terraform.tfstate", "resource_prefix": "module.okta_app_user.okta_app_user.user", "query_field": "app_id", "description": "User assignments for this app"},
        {"entity_name": "okta_app_access_policy_assignment", "state_file": "deployments/app_access_policy_assignment/terraform.tfstate", "resource_prefix": "module.okta_app_access_policy_assignment.okta_app_access_policy_assignment.assignment", "query_field": "app_id", "description": "Access policy assignments for this app"},
    ],
    "okta_app_swa": [
        {"entity_name": "okta_app_group_assignment", "state_file": "deployments/app_group_assignment/terraform.tfstate", "resource_prefix": "module.okta_app_group_assignment.okta_app_group_assignment.app_group_assignment", "query_field": "app_id", "description": "Group assignments for this app"},
        {"entity_name": "okta_app_user", "state_file": "deployments/app_user/terraform.tfstate", "resource_prefix": "module.okta_app_user.okta_app_user.user", "query_field": "app_id", "description": "User assignments for this app"},
        {"entity_name": "okta_app_access_policy_assignment", "state_file": "deployments/app_access_policy_assignment/terraform.tfstate", "resource_prefix": "module.okta_app_access_policy_assignment.okta_app_access_policy_assignment.assignment", "query_field": "app_id", "description": "Access policy assignments for this app"},
    ],
    "okta_app_bookmark": [
        {"entity_name": "okta_app_group_assignment", "state_file": "deployments/app_group_assignment/terraform.tfstate", "resource_prefix": "module.okta_app_group_assignment.okta_app_group_assignment.app_group_assignment", "query_field": "app_id", "description": "Group assignments for this app"},
        {"entity_name": "okta_app_user", "state_file": "deployments/app_user/terraform.tfstate", "resource_prefix": "module.okta_app_user.okta_app_user.user", "query_field": "app_id", "description": "User assignments for this app"},
    ],
    "okta_app_auto_login": [
        {"entity_name": "okta_app_group_assignment", "state_file": "deployments/app_group_assignment/terraform.tfstate", "resource_prefix": "module.okta_app_group_assignment.okta_app_group_assignment.app_group_assignment", "query_field": "app_id", "description": "Group assignments for this app"},
        {"entity_name": "okta_app_user", "state_file": "deployments/app_user/terraform.tfstate", "resource_prefix": "module.okta_app_user.okta_app_user.user", "query_field": "app_id", "description": "User assignments for this app"},
    ],
    "okta_app_basic_auth": [
        {"entity_name": "okta_app_group_assignment", "state_file": "deployments/app_group_assignment/terraform.tfstate", "resource_prefix": "module.okta_app_group_assignment.okta_app_group_assignment.app_group_assignment", "query_field": "app_id", "description": "Group assignments for this app"},
        {"entity_name": "okta_app_user", "state_file": "deployments/app_user/terraform.tfstate", "resource_prefix": "module.okta_app_user.okta_app_user.user", "query_field": "app_id", "description": "User assignments for this app"},
    ],
    "okta_app_three_field": [
        {"entity_name": "okta_app_group_assignment", "state_file": "deployments/app_group_assignment/terraform.tfstate", "resource_prefix": "module.okta_app_group_assignment.okta_app_group_assignment.app_group_assignment", "query_field": "app_id", "description": "Group assignments for this app"},
        {"entity_name": "okta_app_user", "state_file": "deployments/app_user/terraform.tfstate", "resource_prefix": "module.okta_app_user.okta_app_user.user", "query_field": "app_id", "description": "User assignments for this app"},
    ],
    "okta_app_secure_password_store": [
        {"entity_name": "okta_app_group_assignment", "state_file": "deployments/app_group_assignment/terraform.tfstate", "resource_prefix": "module.okta_app_group_assignment.okta_app_group_assignment.app_group_assignment", "query_field": "app_id", "description": "Group assignments for this app"},
        {"entity_name": "okta_app_user", "state_file": "deployments/app_user/terraform.tfstate", "resource_prefix": "module.okta_app_user.okta_app_user.user", "query_field": "app_id", "description": "User assignments for this app"},
    ],
    # POLICIES MODULE
    "okta_policy_mfa": [
        {"entity_name": "okta_policy_rule_mfa", "state_file": "deployments/policy_rule_mfa/terraform.tfstate", "resource_prefix": "module.okta_policy_rule_mfa.okta_policy_rule_mfa.policy_rule", "query_field": "policy_id", "id_field": "policy_rule_id", "description": "MFA policy rules"},
    ],
    "okta_policy_password": [
        {"entity_name": "okta_policy_rule_password", "state_file": "deployments/policy_rule_password/terraform.tfstate", "resource_prefix": "module.okta_policy_rule_password.okta_policy_rule_password.policy_rule", "query_field": "policy_id", "id_field": "policy_rule_id", "description": "Password policy rules"},
    ],
    "okta_policy_signon": [
        {"entity_name": "okta_policy_rule_sign_on", "state_file": "deployments/policy_rule_sign_on/terraform.tfstate", "resource_prefix": "module.okta_policy_rule_sign_on.okta_policy_rule_sign_on.policy_rule", "query_field": "policy_id", "id_field": "policy_signon_rule_id", "description": "SignOn policy rules"},
    ],
    "okta_policy_profile_enrollment": [
        {"entity_name": "okta_policy_rule_profile_enrollment", "state_file": "deployments/policy_rule_profile_enrollment/terraform.tfstate", "resource_prefix": "module.okta_policy_rule_profile_enrollment.okta_policy_rule_profile_enrollment.policy_rule", "query_field": "policy_id", "id_field": "policy_rule_id", "description": "Profile enrollment policy rules"},
        {"entity_name": "okta_policy_profile_enrollment_apps", "state_file": "deployments/policy_profile_enrollment_apps/terraform.tfstate", "resource_prefix": "module.okta_policy_profile_enrollment_apps.okta_policy_profile_enrollment_apps.app", "query_field": "policy_id", "id_field": "app_id", "description": "Profile enrollment apps"},
    ],
    # AUTH SERVERS MODULE
    "okta_auth_server": [
        {"entity_name": "okta_auth_server_scope", "state_file": "deployments/auth_server_scope/terraform.tfstate", "resource_prefix": "module.okta_auth_server_scope.okta_auth_server_scope.scope", "query_field": "auth_server_id", "id_field": "scope_id", "description": "Authorization server scopes"},
        {"entity_name": "okta_auth_server_claim", "state_file": "deployments/auth_server_claim/terraform.tfstate", "resource_prefix": "module.okta_auth_server_claim.okta_auth_server_claim.claim", "query_field": "auth_server_id", "id_field": "claim_id", "description": "Authorization server claims"},
        {"entity_name": "okta_auth_server_policy", "state_file": "deployments/auth_server_policy/terraform.tfstate", "resource_prefix": "module.okta_auth_server_policy.okta_auth_server_policy.policy", "query_field": "auth_server_id", "id_field": "policy_id", "description": "Authorization server policies"},
        {"entity_name": "okta_auth_server_policy_rule", "state_file": "deployments/auth_server_policy_rule/terraform.tfstate", "resource_prefix": "module.okta_auth_server_policy_rule.okta_auth_server_policy_rule.policy_rule", "query_field": "auth_server_id", "id_field": "policy_rule_id", "description": "Authorization server policy rules"},
        {"entity_name": "okta_trusted_server", "state_file": "deployments/trusted_server/terraform.tfstate", "resource_prefix": "module.okta_trusted_server.okta_trusted_server.trusted_server", "query_field": "auth_server_id", "id_field": "auth_server_id", "description": "Trusted authorization servers"},
    ],
    # ADMIN MODULE
    "okta_admin_role_custom": [
        {"entity_name": "okta_resource_set", "state_file": "deployments/resource_set/terraform.tfstate", "resource_prefix": "module.okta_resource_set.okta_resource_set.resource_set", "query_field": "role_id", "id_field": "resource_set_id", "description": "Resource sets for custom admin role"},
    ],
    # APP SIGNON POLICY
    "okta_app_signon_policy": [
        {"entity_name": "okta_app_signon_policy_rule", "state_file": "deployments/app_signon_policy_rule/terraform.tfstate", "resource_prefix": "module.okta_app_signon_policy_rule.okta_app_signon_policy_rule.policy_rule", "query_field": "app_policy_id", "id_field": "policy_id", "description": "App signon policy rules"},
    ],
}

# ---------------------------------------------------------------------------
# Alternate terraform_key spellings -> canonical terraform_key.
# Derived from COLLECTION_STATE_MAP entries that resolve to the same state file
# as a canonical key (the one present in RESOURCE_COLLECTION_MAP). Used to seed
# terraform_registry.aliases and to resolve OkTf-sourced rows whose keys are
# aliases. Curated; extend as new alias spellings appear.
# ---------------------------------------------------------------------------
TERRAFORM_KEY_ALIASES = {
    "okta_global_signon_policies": "okta_policy_sign_on",
    "okta_policy_signon": "okta_policy_sign_on",
    "okta_password_policy": "okta_policy_password",
    "okta_authenticator_enroll_policies": "okta_policy_mfa",
}
