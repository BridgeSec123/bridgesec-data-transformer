RESOURCE_COLLECTION_MAP = {
    "Users": [
        {"Users": "okta_user"},
        {"User Schema Properties": "okta_user_schema_property"},
        {"User Group Memberships": "okta_user_group_memberships"},
        {"User Base Schema Properties": "okta_user_base_schema_property"},
        {"User Admin Roles": "okta_user_admin_roles"},
        {"User Risk": "okta_user_risk"},
    ],
    "User Types": [
        {"User Types": "okta_user_type"}
    ],
    "Groups": [
        {"Groups": "okta_group"},
        {"Group Schema Property": "okta_group_schema_property"},
        {"Group Rules": "okta_group_rule"},
        {"Group Roles": "okta_group_role"},
        {"Group Memberships": "okta_group_memberships"},
    ],
    "Brands": [
        {"Brands": "okta_brand"},
        {"Email Domain": "okta_email_domain"}
    ],
    "Device": [
        {"Policy Device Assurance Android": "okta_policy_device_assurance_android"},
        {"Policy Device Assurance IOS": "okta_policy_device_assurance_ios"},
        {"Policy Device Assurance Macos": "okta_policy_device_assurance_macos"},
        {"Policy Device Assurance Windows": "okta_policy_device_assurance_windows"},
    ],
    "Themes": [
        {"Themes": "okta_theme"}
    ],
    "Email": [
        {"Email SMTP Server": "okta_email_smtp_server"}
    ],
    "Rate Limits": [
        {"Principal Rate Limit": "okta_principal_rate_limits"},
        {"Rate Limit Admin Notification": "okta_rate_limit_admin_notification"},
        {"Rate Limit Admin Notification Settings": "okta_rate_limit_admin_notification_settings"},
        {"Rate Limit Warning Threshold Percentage": "okta_rate_limit_warning_threshold_percentage"}
    ],
    "Entitlements": [
        {"Entitlement Bundle": "okta_entitlement_bundle"},
        {"Principal Entitlement": "okta_principal_entitlements"},
        {"Entitlements":"okta_entitlements"}
    ],
    "Requests": [
        {"Request Condition": "okta_request_conditions"},
        {"Request Sequence": "okta_request_sequences"},
        {"Request Settings": "okta_request_settings"},
        {"Request Type": "okta_request_types"},
    ],
    "Catalog": [
        {"Catalog Entry Default": "okta_catalog_entry_default"},
        {"Catalog Entry User Access Request Fields": "okta_catalog_entry_user_access_request_fields"},
        {"End User My Requests": "okta_end_user_my_requests"},
    ],
    "Reviews": [
        {"Review": "okta_reviews"}
    ],
    "Sms Template": [
        {"Sms Template": "okta_template_sms"}
    ],
    # "Captcha": [
    #     {"Captchas": "okta_captcha"},
    #     {"Captacha Wide Org Settings": "okta_captcha_org_wide_settings"},
    # ],
    "Organization Security": [
        {"Organization Security": "okta_org_configuration"}
    ],
    "Threat Insights": [
        {"Threat Insights": "okta_threat_insight_settings"}
    ],
    "Authenticator": [
        {"Authenticator": "okta_authenticator"},
        {"Factor": "okta_factor"},
    ],
    "Authorization Servers": [
        {"Auth Server": "okta_auth_server"},
        {"Auth Server Claim": "okta_auth_server_claim"},
        {"Auth Server Policy": "okta_auth_server_policy"},
        {"Auth Server Policy Rule": "okta_auth_server_policy_rule"},
        {"Auth Server Scope": "okta_auth_server_scope"},
        {"Auth Server Client": "okta_auth_server_clients"},
        {"Auth Server Key": "okta_auth_server_keys"},
    ],
    "Identity Providers": [
        {"IDP OIDC": "okta_idp_oidc"},
        {"IDP SAML": "okta_idp_saml"},
        {"IDP SOCIAL": "okta_idp_social"},
    ],
    "Policy": [
        {"Policy MFA": "okta_policy_mfa"},
        {"Policy Rule Mfa": "okta_policy_rule_mfa"},
        {"Policy Password": "okta_policy_password"},
        {"Policy Rule Password": "okta_policy_rule_password"},
        {"Policy Profile Enrollment": "okta_policy_profile_enrollment"},
        {"Policy Rule Profile Enrollment": "okta_policy_rule_profile_enrollment"},
        {"Policy Sign On": "okta_policy_sign_on"},
        {"Policy Rule Sign On": "okta_policy_rule_sign_on"},
        {"Policy Profile Enrollment apps": "okta_policy_profile_enrollment_apps"},
        {"Policy Rule Idp Discovery": "okta_policy_rule_idp_discovery"},
    ],
    "Network Zone": [
        {"Network Zone": "okta_network_zone"}
    ],
    "Behavior": [
        {"Behavior": "okta_behavior"}
    ],
    "Administrator Roles": [
        {"Admin Role Custom": "okta_admin_role_custom"},
        # {"Admin Role Targets": "okta_admin_role_targets"},
        # {"Role Subscription": "okta_role_subscription"},
        {"Resoure set": "okta_resource_set"},
    ],
      "Trusted Origins": [
        {"Trusted Origin": "okta_trusted_origin"},
        # {"Trusted Server": "okta_trusted_server"},
    ],
    "Inline Hooks": [
        {"Inline Hook": "okta_inline_hook"}
    ],
    "Event Hook": [
        {"Event Hook": "okta_event_hook"}
    ],
    "Hook Keys": [
        {"Hook Key": "okta_hook_key"}
    ],
    "Api Tokens": [
        {"Api Token": "okta_api_token"}
    ],
    "Domains": [
        {"Domain": "okta_domain"}
    ],
    "Push Providers": [
        {"Push Provider": "okta_push_provider"}
    ],
    "Api Service Integrations": [
        {"Api Service Integration": "okta_api_service_integration"}
    ],
    "UI Schemas": [
        {"Ui Schema": "okta_ui_schema"}
    ],
    "Link": [
        {"Link Definition": "okta_link_definition"}
    ],
    "Entity Risk Policy": [
        {"Entity Risk Policy": "okta_entity_risk_policy"},
        {"Entity Risk Policy Rule": "okta_entity_risk_policy_rule"},
    ],
    "Applications": [
        {"App Oauth": "okta_app_oauth"},
        {"App Saml": "okta_app_saml"},
        {"App Group Assignments": "okta_app_group_assignments"},
        {"App Oauth Role Assignment": "okta_app_oauth_role_assignment"},
        {"App Access Policy Assignment": "okta_app_access_policy_assignment"},
        {"App Signon Policy": "okta_app_signon_policy"},
        {"App Signon Policy Rule": "okta_app_signon_policy_rule"},
        {"App Saml Settings": "okta_app_saml_app_settings"},
        {"App Group Assignment": "okta_app_group_assignment"},
        {"App Shared Credentials": "okta_app_shared_credentials"},
        # {"App Saml Settings": "okta_app_saml_settings"},
        {"App Bookmark": "okta_app_bookmark"},
        {"App Auto Login": "okta_app_auto_login"},
        {"App Three Field": "okta_app_three_field"},
        {"App Secure Password Store" : "okta_app_secure_password_store"},
        {"App User Schema Property" : "okta_app_user_schema_property"},
        {"App User Base Schema Property" : "okta_app_user_base_schema_property"},
        {"App Basic Auth": "okta_app_basic_auth"},
        {"App SWA": "okta_app_swa"},
        {"App User": "okta_app_user"},
        {"App Oauth Api Scope": "okta_app_oauth_api_scope"},
        {"App Token": "okta_app_token"},
        {"App Oauth Post Logout Redirect Uri": "okta_app_oauth_post_logout_redirect_uri"},
        {"App Oauth Redirect Uri": "okta_app_oauth_redirect_uri"},
        {"App Connection": "okta_app_connection"},
        {"App Federated Claim": "okta_app_federated_claim"},
        {"App Push Groups": "okta_app_push_groups"},
    ]
}

# Entity ID mapping for comparison - maps entity name to its unique ID field
ENTITY_ID_MAPPING = {
    # Users
    "Users": "user_id",
    "User Schema Properties": "user_id",
    "User Group Memberships": "user_id",
    "User Base Schema Properties": "user_id",
    "User Admin Roles": "user_id",
    "User Types": "user_type_id",
    "User Risk": "user_id",

    "Policy Rule Password":"policy_password_id",

    "Entitlements":"id",
    "Factor": "provider_id",
    "Authenticator": "key",
    # Groups
    "Groups": "group_id",
    "Group Schema Property": "id",
    "Group Rules": "group_rule_id",
    "Group Roles": "group_role_id",
    "Group Memberships": "group_id",

    # Brands
    "Brands": "brand_id",
    "Email Domain": "email_domain_id",

    # "Behavior":"behavior_id",

    # Device Assurance Policies
    "Policy Device Assurance Android": "device_id",
    "Policy Device Assurance IOS": "device_id",
    "Policy Device Assurance Macos": "device_id",
    "Policy Device Assurance Windows": "device_id",

    # Email
    "Email SMTP Server": "id",

    # Rate Limits
    "Principal Rate Limit": "rate_limit_id",
    "Rate Limit Admin Notification": "notification_id",
    "Rate Limit Admin Notification Settings": "notification_id",
    "Rate Limit Warning Threshold Percentage": "threshold_id",

    # Entitlements
    "Entitlement Bundle": "bundle_id",
    "Principal Entitlement": "entitlement_id",

    # Requests
    "Request Condition": "condition_id",
    "Request Sequence": "sequence_id",
    "Request Settings": "id",
    "Request Type": "request_id",

    # Catalog
    "Catalog Entry Default": "entry_id",
    "Catalog Entry User Access Request Fields": "field_id",
    "End User My Requests": "request_id",

    # Reviews
    "Review": "review_id",

    # SMS Template
    "Sms Template": "sms_id",

    "Themes":"brand_id",

    # Organization Security
    "Organization Security": "id",

    # Threat Insights
    "Threat Insights": "action",

    # Authorization Servers
    "Auth Server": "auth_server_id",
    "Auth Server Client": "token_id",
    "Auth Server Key": "key_id",

    # Identity Providers
    "IDP OIDC": "idp_id",
    "IDP SAML": "idp_id",
    "IDP SOCIAL": "idp_id",

    # Policies
    "Policy MFA": "policy_id",
    "Policy Rule Mfa":"policy_rule_id",
    "Policy Password": "policy_id",
    "Policy Profile Enrollment": "policy_id",
    "Policy Sign On": "policy_signon_id",
    "Policy Rule Profile Enrollment":"policy_profile_rule_id",

    # Network Zone
    "Network Zone": "network_id",

    # Behavior
    "Behavior": "behavior_id",

    # Domain
    "Domain": "domain_id",

    # Administrator Roles
    "Admin Role Custom": "custom_role_id",

    # Trusted Origins
    "Trusted Origin": "trusted_id",

    # Inline Hooks
    "Inline Hook": "inline_hook_id",

    # Event Hooks
    "Event Hook": "event_id",
    "Hook Key": "hook_key_id",
    "Api Token": "token_id",

    # Link Definition
    "Link Definition": "primary_name",

    # Applications
    "App Oauth": "app_id",
    "App Saml": "app_id",
    "App Saml Settings":"app_id",
    "App Group Assignments": "app_id",
    "App Access Policy Assignment": "app_id",
    "App Signon Policy": "app_policy_id",
    "App Signon Policy Rule":"policy_rule_id",
    "App Oauth Role Assignment": "client_id",
    "App Shared Credentials":"label",
    "App Group Assignment": "app_id",
    "App Bookmark": "app_id",
    "App Auto Login": "app_id",
    "App Three Field": "app_id",
    "App Secure Password Store": "app_id",
    "App User Schema Property": "app_id",
    "App User Base Schema Property": "app_id",
    "App Basic Auth": "app_id",
    "App SWA": "app_id",
    "App User": "user_id",
    "App Oauth Post Logout Redirect Uri":"app_id",
    "App Oauth Redirect Uri":"app_id",
    "App Oauth Api Scope":"app_id",
    "App Token": "token_id",
    "App Connection": "app_id",
    "App Federated Claim": "claim_id",
    "App Push Groups": "push_group_id",
    "Push Provider": "push_provider_id",
    "Api Service Integration": "api_service_integration_id",
    "Ui Schema": "ui_schema_id",
    "Entity Risk Policy": "policy_id",
    "Entity Risk Policy Rule": "policy_rule_id",
}

NON_EDITABLE_FIELDS = {
    # User entities
    "Users": ["user_id"],
    "User Schema Properties": ["user_id"],
    "User Group Memberships": ["user_id"],
    "User Base Schema Properties": ["user_id"],
    "User Admin Roles": ["user_id"],
    "User Types": ["user_type_id"],
    "User Risk": ["user_id", "risk_id"],

    "Entitlements":["data_type"],

    # Application entities
    "App Oauth": ["app_id"],
    "App Saml": ["app_id"],
    "App Saml Settings":["app_id"],
    "App Bookmark": ["app_id"],
    "App Auto Login": ["app_id"],
    "App Basic Auth": ["app_id"],
    "App SWA": ["app_id"],
    "App Three Field": ["app_id"],
    "App Group Assignments": ["app_id"],
    "App Group Assignment": ["app_id"],
    "App Signon Policy": ["app_policy_id"],
    "App User Base Schema Property": ["app_id"],
    "App User Schema Property": ["app_id"],
    "App Access Policy Assignment": ["app_id"],
    "App Oauth Role Assignment": ["client_id"],
    "App Secure Password Store": ["app_id"],
    "App Oauth Post Logout Redirect Uri":["app_id"],
    "App Oauth Redirect Uri":["app_id"],
    "App Oauth Api Scope":["app_id"],
    "App Token": ["token_id", "client_id", "user_id", "created", "expires_at", "scopes", "issuer", "status"],
    "App Connection": ["status"],
    "App Federated Claim": ["claim_id", "app_id"],
    "App Push Groups": ["push_group_id", "app_id", "source_group_id", "status"],
    "Push Provider": ["push_provider_id", "last_updated_date"],
    "Api Service Integration": ["api_service_integration_id", "name", "config_guide_url", "created", "created_at"],
    "Ui Schema": ["ui_schema_id", "created", "last_updated"],

    # Policy entities
    "Policy MFA": ["policy_id"],
    "Policy Rule Mfa":["policy_rule_id"],
    "Policy Password": ["policy_id", "priority"],
    "Policy Profile Enrollment": ["policy_id", "priority"],
    "Policy Rule Profile Enrollment":["policy_profile_rule_id"],
    "Policy Sign On": ["policy_signon_id", "priority"],
    "Policy Rule Password":["policy_password_id"],

    # Auth Server entities
    "Auth Server": ["auth_server_id"],
    "Auth Server Client": ["token_id", "auth_server_id", "client_id", "created", "expires_at", "issuer", "last_updated", "scopes", "status", "user_id"],
    "Auth Server Key": ["key_id", "auth_server_id", "alg", "e", "kid", "n", "status", "use"],

    # Identity Provider entities
    "IDP OIDC": ["idp_id"],
    "IDP SAML": ["idp_id"],
    "IDP SOCIAL": ["idp_id"],

    # Group entities
    "Groups": ["group_id"],
    "Group Rules": ["group_rule_id"],
    "Group Roles": ["group_role_id"],
    "Group Memberships": ["group_id"],
    "Group Schema Property": ["group_id"],

    # Brand entities
    "Brands": ["brand_id"],
    "Email Domain": ["email_domain_id"],

    "Organization Security": ["id"],

    # Device Assurance Policy entities
    "Policy Device Assurance Android": ["device_id"],
    "Policy Device Assurance IOS": ["device_id"],
    "Policy Device Assurance Macos": ["device_id"],
    "Policy Device Assurance Windows": ["device_id"],

    # Email
    "Email SMTP Server": ["id"],

    # Rate Limits
    "Principal Rate Limit": ["rate_limit_id", "principal_id", "created_by", "created_date", "last_update", "last_updated_by", "org_id"],
    "Rate Limit Admin Notification": ["notification_id"],
    "Rate Limit Admin Notification Settings": ["notification_id"],
    "Rate Limit Warning Threshold Percentage": ["threshold_id"],

    # Entitlements
    "Entitlement Bundle": ["bundle_id"],
    "Principal Entitlement": ["entitlement_id"],

    # Requests
    "Request Condition": ["condition_id"],
    "Request Sequence": ["sequence_id"],
    "Request Settings": ["id"],
    "Request Type": ["request_id"],

    # Catalog
    "Catalog Entry Default": ["entry_id"],
    "Catalog Entry User Access Request Fields": ["field_id"],
    "End User My Requests": ["request_id"],

    # Reviews
    "Review": ["review_id"],

    # SMS Template
    "Sms Template": ["sms_id"],

    "Factor": ["provider_id"],
    "Authenticator": ["key"],

    # Network Zone
    "Network Zone": ["network_id", "system"],

    # Behavior
    "Behavior": ["behavior_id"],

    # Domain
    "Domain": ["domain_id", "validation_status", "dns_records", "public_certificate"],

    # Administrator Roles
    "Admin Role Custom": ["custom_role_id"],

    # Trusted Origins
    "Trusted Origin": ["trusted_id"],

    # Inline Hooks
    "Inline Hook": ["inline_hook_id"],

    # Event Hooks
    "Event Hook": ["event_id"],
    "Hook Key": ["hook_key_id", "key_id", "created", "is_used", "last_updated"],
    "Api Token": ["token_id", "created"],
    "Entity Risk Policy": ["policy_id", "name", "status"],
    "Entity Risk Policy Rule": ["policy_rule_id", "policy_id"],
}
