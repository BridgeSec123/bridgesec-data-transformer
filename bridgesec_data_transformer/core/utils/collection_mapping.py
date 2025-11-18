RESOURCE_COLLECTION_MAP = {
    "Users": [
        {"User": "okta_user"},
        {"User Schema Properties": "okta_user_schema_properties"},
        {"User Group Memberships": "okta_user_group_memberships"},
        {"User Base Schema Properties": "user_base_schema_properties"},
        {"User Admin Roles": "user_admin_roles"},
    ],
    "User Types": [
        {"User Type": "okta_user_type"}
    ],
    "Groups": [
        {"Groups": "okta_group"},
        {"Group Schema Property": "okta_group_schema_property"},
        {"Group Rules": "okta_group_rule"},
        {"Group Roles": "okta_group_role"},
        {"Group Memberships": "okta_group_memberships"},
    ],
    "Brands": [
        {"Brand": "okta_brand"},
        {"Email Domain": "okta_email_domain"}
    ],
    "Device": [
        {"Policy Device Assurance Android": "okta_policy_device_assurance_android"},
        {"Policy Device Assurance IOS": "okta_policy_device_assurance_ios"},
        {"Policy Device Assurance Macos": "okta_policy_device_assurance_macos"},
        {"Policy Device Assurance Windows": "okta_policy_device_assurance_windows"},
    ],
    # "Theme": [
    #     {"Theme": "okta_theme"}
    # ],
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
        {"Principal Entitlement": "okta_principal_entitlements"}
    ],
    "Requests": [
        {"Request Condition": "okta_request_conditions"},
        {"Request Sequence": "okta_request_sequences"},
        {"Request Settings": "okta_request_settings"}
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
    # +    {"Factor": "okta_factors"},
    ],
    "Authorization Servers": [
        {"Auth Server": "okta_auth_server"},
        # {"Auth Server Claim": "okta_auth_server_claim"},
        # {"Auth Server Policy": "okta_auth_server_policy"},
        # {"Auth Server Policy Rule": "okta_auth_server_policy_rule"},
        # {"Auth Server Scope": "okta_auth_server_scope"},
        # {"Auth Server Policy": "okta_auth_server_policy"},
        # {"Auth Server Policy Rule": "okta_auth_server_policy_rule"},
    ],
    "Identity Providers": [
        {"IDP OIDC": "okta_idp_oidc"},
        {"IDP SAML": "okta_idp_saml"},
        {"IDP SOCIAL": "okta_idp_social"},
    ],
    "Policy": [
        {"Policy MFA": "okta_policy_mfa"},
        # {"Policy Rule Mfa": "okta_policy_rule_mfa"},
        {"Policy Password": "okta_policy_password"},
        # {"Policy Rule Password": "okta_policy_rule_password"},
        {"Policy Profile Enrollment": "okta_policy_profile_enrollment"},
        # {"Policy Rule Profile Enrollment": "okta_policy_rule_profile_enrollment"},
        {"Policy Sign On": "okta_policy_sign_on"},
        # {"Policy Rule Sign On": "okta_policy_rule_sign_on"},
         {"Policy Profile Enrollment apps": "okta_policy_profile_enrollment_apps"},
        # {"Policy Rule Idp Discovery": "okta_policy_rule_idp_discovery"},
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
        # {"Resoure set": "okta_resource_set"},
    ],
      "Trusted Origins": [
        {"Trusted Origin": "okta_trusted_origin"},
        # {"Trusted Server": "okta_trusted_server"},
    ],
    "Inline Hooks": [
        {"Inline Hook": "okta_inline_hook"}
    ],
    "Event_Hook": [
        {"Event Hook": "okta_event_hook"}
    ],
    # "Domains": [
    #     {"Domain": "okta_domain"}
    # ],
    "Link": [
        {"Link Definition": "okta_link_definition"}
    ],
    "Applications": [
        {"App Oauth": "okta_app_oauth", "non_editable_field": ["app_id"]},
        {"App Saml": "okta_app_saml"},
        {"App Group Assignments": "okta_app_group_assignments"},
        # {"App Oauth Role Assignment": "okta_app_oauth_role_assignment"},
        {"App Access Policy Assignment": "okta_app_access_policy_assignment"},
        {"App Signon Policy": "okta_app_signon_policy"},
        {"App Signon Policy Rule": "okta_app_signon_policy_rule"},
        # {"App Saml Settings": "okta_app_saml_app_settings"},
        {"App Group Assignment": "okta_app_group_assignment"},
        # {"App Shared Credentials": "okta_app_shared_credentials"},
         {"App Bookmark": "okta_app_bookmark"},
         {"App Auto Login": "okta_app_auto_login"},
         {"App Three Field": "okta_app_three_field"},
         {"App Secure Password Store" : "okta_app_secure_password_store"},
         {"App User Schema Property" : "okta_app_user_schema_property"},
         {"App User Base Schema Property" : "okta_app_user_base_schema_property"},
         {"App Basic Auth": "okta_app_basic_auth"},
         {"App Swa": "okta_app_swa"},
         {"App User": "okta_app_user"},
        {"App Oauth Api Scope": "okta_app_oauth_api_scope"},
        {"APP Oauth Post Logout Redirect Uri": "okta_app_oauth_post_logout_redirect_uri"},
        {"App Oauth Redirect Uri": "okta_app_oauth_redirect_uri"},
    ]
}

# Entity ID mapping for comparison - maps entity name to its unique ID field
ENTITY_ID_MAPPING = {
    # Users
    "User": "user_id",
    "User Schema Properties": "user_id",
    "User Group Memberships": "user_id",
    "User Base Schema Properties": "user_id",
    "User Admin Roles": "user_id",
    "User Type": "user_type_id",

    # Groups
    "Groups": "group_id",
    "Group Schema Property": "id",
    "Group Rules": "group_rule_id",
    "Group Roles": "group_role_id",
    "Group Memberships": "id",

    # Brands
    "Brand": "brand_id",

    # Device Assurance Policies
    "Policy Device Assurance Android": "device_id",
    "Policy Device Assurance IOS": "device_id",
    "Policy Device Assurance Macos": "device_id",
    "Policy Device Assurance Windows": "device_id",

    # Email
    "Email SMTP Server": "id",

    # Rate Limits
    "Principal Rate Limit": "id",
    "Rate Limit Admin Notification": "id",
    "Rate Limit Admin Notification Settings": "id",
    "Rate Limit Warning Threshold Percentage": "id",

    # Entitlements
    "Entitlement Bundle": "id",
    "Principal Entitlement": "id",

    # Requests
    "Request Condition": "id",
    "Request Sequence": "id",
    "Request Settings": "id",

    # SMS Template
    "Sms Template": "sms_id",

    # Organization Security
    "Organization Security": "id",

    # Threat Insights
    "okta_threat_insight_settings": "action",

    # Authorization Servers
    "Auth Server": "auth_server_id",

    # Identity Providers
    "IDP OIDC": "idp_id",
    "IDP SAML": "idp_id",
    "IDP SOCIAL": "idp_id",

    # Policies
    "Policy MFA": "policy_id",
    "Policy Password": "policy_id",
    "Policy Profile Enrollment": "policy_id",
    "Policy Sign On": "policy_signon_id",

    # Network Zone
    "Network Zone": "network_id",

    # Behavior
    "Behavior": "behavior_id",

    # Administrator Roles
    "Admin Role Custom": "custom_role_id",

    # Trusted Origins
    "Trusted Origin": "trusted_id",

    # Inline Hooks
    "Inline Hook": "inline_hook_id",

    # Event Hooks
    "Event_Hook": "event_id",

    # Link Definition
    "okta_link_definition": "primary_name",

    # Applications
    "App Oauth": "app_id",
    "App Saml": "app_id",
    "App Group Assignments": "app_id",
    "App Access Policy Assignment": "app_id",
    "App Signon Policy": "app_policy_id",
    "App Group Assignment": "app_id",
    "App Bookmark": "app_id",
    "App Auto Login": "app_id",
    "App Three Field": "app_id",
    "App Secure Password Store": "app_id",
    "App User Schema Property": "app_id",
    "App User Base Schema Property": "app_id",
    "App Basic Auth": "app_id",
    "App Swa": "app_id",
    "App User": "app_id",
}

NON_EDITABLE_FIELDS = {
    # User entities
    "User": ["user_id"],
    "User Schema Properties": ["user_id"],
    "User Group Memberships": ["user_id"],
    "User Base Schema Properties": ["user_id"],
    "User Admin Roles": ["user_id"],
    "User Type": ["user_type_id"],

    # Application entities
    "App Oauth": ["app_id"],
    "App Saml": ["app_id"],
    "App Bookmark": ["app_id"],
    "App Auto Login": ["app_id"],
    "App Basic Auth": ["app_id"],
    "App Swa": ["app_id"],
    "App Secure Password Store": ["app_id"],
    "App Three Field": ["app_id"],
    "App Group Assignments": ["app_id"],
    "App Access Policy Assignment": ["app_id"],
    "App Group Assignment": ["app_id"],
    "App Signon Policy": ["app_policy_id"],
    "App User Schema Property": ["app_id"],
    "App User Base Schema Property": ["app_id"],

    # Policy entities
    "Policy MFA": ["policy_id"],
    "Policy Password": ["policy_id", "priority"],
    "Policy Profile Enrollment": ["policy_id", "priority"],
    "Policy Sign On": ["policy_signon_id", "priority"],

    # Auth Server entities
    "Auth Server": ["auth_server_id"],

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
    "Brand": ["brand_id"],

    # Device Assurance Policy entities
    "Policy Device Assurance Android": ["device_id"],
    "Policy Device Assurance IOS": ["device_id"],
    "Policy Device Assurance Macos": ["device_id"],
    "Policy Device Assurance Windows": ["device_id"],

    # Email
    "Email SMTP Server": ["id"],

    # Rate Limits
    "Principal Rate Limit": ["id", "principal_id", "created_by", "created_date", "last_update", "last_updated_by", "org_id"],
    "Rate Limit Admin Notification": ["id"],
    "Rate Limit Admin Notification Settings": ["id"],
    "Rate Limit Warning Threshold Percentage": ["id"],

    # Entitlements
    "Entitlement Bundle": ["id"],
    "Principal Entitlement": ["id"],

    # Requests
    "Request Condition": ["id"],
    "Request Sequence": ["id"],
    "Request Settings": ["id"],

    # SMS Template
    "Sms Template": ["sms_id"],

    # Network Zone
    "Network Zone": ["network_id"],

    # Behavior
    "Behavior": ["behavior_id"],

    # Administrator Roles
    "Admin Role Custom": ["custom_role_id"],

    # Trusted Origins
    "Trusted Origin": ["trusted_id"],

    # Inline Hooks
    "Inline Hook": ["inline_hook_id"],

    # Event Hooks
    "Event_Hook": ["event_id"],
}
