# Singleton resources with fixed identifiers (no real ID field)
SINGLETON_RESOURCE_IDENTIFIERS = {
    "okta_threat_insight_settings": "threat_insight",
    "okta_org_configuration": "org_configuration",
}

ENTITY_TARGET_FIELD_MAP = {
    # Application entities
    "okta_app_oauth": "app_id",
    "okta_app_swa": "app_id",
    "okta_app_saml": "app_id",
    "okta_app_auto_login": "app_id",
    "okta_app_basic_auth": "app_id",
    "okta_app_bookmark": "app_id",
    "okta_app_group_assignments": "app_id",
    "okta_app_group_assignement": "app_id",
    "okta_app_user_base_schema_property": "app_id",
    "okta_app_user_schema_property": "app_id",
    "okta_app_user": "user_id",
    "okta_app_group_assignment": "app_id",
    "okta_app_access_policy_assignment": "app_id",
    "okta_app_secure_password_store": "app_id",
    "okta_app_three_field": "app_id",
    "okta_app_oauth_server_policy": "app_id",
    "okta_app_oauth_redirect_uri" : "app_id",
    "okta_app_oauth_post_redirect_uri" : "app_id",

    # User and Group entities
    "okta_user": "user_id",
    "okta_user_type": "user_type_id",
    "User Group Memberships" : "user_id",
    "Group Memberships" : "group_id",
    "okta_group_memberships":"group_id",
    "okta_group": "group_id",
    "okta_group_role": "group_role_id",
    "okta_group_rule": "group_rule_id",

    # Brand entities
    "okta_brand": "brand_id",

    # Network and Security entities
    "okta_network_zone": "network_id",
    "okta_behavior": "behavior_id",

    # Email entities
    "okta_email_domain": "email_domain_id",
    "okta_email_smtp_server": "smtp_id",

    # Device Assurance entities
    "okta_policy_device_assurance_windows": "device_id",
    "okta_policy_device_assurance_macos": "device_id",
    "okta_policy_device_assurance_ios": "device_id",
    "okta_policy_device_assurance_android": "device_id",

    # Hook entities
    "okta_event_hook": "event_id",
    "okta_inline_hook": "inline_hook_id",

    # Template entities
    "okta_template_sms": "template_id",

    # Authenticator entities
    "okta_authenticator": "authenticator_id",

    # IDP entities
    "okta_idp_saml": "idp_id",
    "okta_idp_oidc": "idp_id",
    "okta_idp_social": "idp_id",

    "okta_trusted_origin": "trusted_id",

    # Organization entities
    "okta_org_configuration": "org_id",

    # Link Definition (uses primary_name as identifier)
    "okta_link_definition": "primary_name",

    # Entity builders with multiple IDs
    "okta_auth_server": ["auth_server_id", "scope_id", "claim_id", "policy_id", "policy_rule_id", "trusted_id"],

    "okta_policy_mfa": ["policy_id", "policy_rule_id"],

    "okta_app_signon_policy": ["app_policy_id", "policy_rule_id"],

    "okta_policy_password": ["policy_id", "policy_password_id"],

    "okta_policy_profile_enrollment": ["policy_id", "policy_profile_rule_id", "app_id"],

    "okta_policy_sign_on": ["policy_signon_id", "policy_signon_rule_id"],

    "okta_admin_role_custom": ["custom_role_id", "role_id"],
}