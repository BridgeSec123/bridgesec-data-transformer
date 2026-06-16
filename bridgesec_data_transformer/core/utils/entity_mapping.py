import logging

logger = logging.getLogger(__name__)

IDP_BASE_CONFIG = {
    "okta_endpoint": "/api/v1/idps",
    "attributes": ["id", "issuerMode","name","protocol", "policy", "type", "status"],
}

ENTITY_TYPE_MAPPING = {
    "authenticators": {
        "okta_endpoint": "/api/v1/authenticators",
        "attributes": ["key", "name", "status", "settings", "provider"],
    },
    "trusted_origins": {
        "okta_endpoint": "/api/v1/trustedOrigins",
        "attributes": ["id","name", "origin", "scopes", "status"],
    },
    "okta_user": {"okta_endpoint": "/api/v1/users", "attributes": ["id", "profile", "realmId"]},
    "user_factors": {
        "okta_endpoint": "/api/v1/users/{userId}/factors",
        "attributes": ["id", "status"],
    },
    "user_admin_roles": {
        "okta_endpoint": "/api/v1/users/{userId}/roles",
        "attributes": ["id", "type", "disableNotifications"],
    },
    "okta_groups": {
        "okta_endpoint": "/api/v1/groups",
        "attributes": ["id", "profile"],
    },
    "group_owners": {
        "okta_endpoint": "/api/v1/groups/{groupId}/owners",
        "attributes": ["id"],
    },
    "group_memberships": {
        "okta_endpoint": "/api/v1/groups/{groupId}/users",
        "attributes": ["id", ],
    },
    "group_schemas": {
        "okta_endpoint": "/api/v1/meta/schemas/group/default",
        "attributes": ["title", "type", "definitions", "description"],
    },
    "group_rules": {
        "okta_endpoint": "api/v1/groups/rules",
        "attributes": ["id", "name", "actions", "conditions", "status"],
    },
    "group_roles": {
        "okta_endpoint": "api/v1/groups/{group_id}/roles",
        "attributes": [
            "id",
            "type",
            "description",
            "status",
            "targetGroupIds",
            "targetAppInstanceIds",
            "disableNotifications",
        ],
    },
    "user_types": {
        "okta_endpoint": "/api/v1/meta/types/user",
        "attributes": ["id", "name", "displayName", "description"],
    },
    "brands": {
        "okta_endpoint": "/api/v1/brands",
        "attributes": [
            "id",
            "name",
            "removePoweredByOkta",
            "customPrivacyPolicyUrl",
            "agreeToCustomPrivacyPolicy",
            "defaultApp",
            "locale",
        ],
    },
    "event_hooks": {
        "okta_endpoint": "/api/v1/eventHooks",
        "attributes": ["id", "name", "events", "channel"],
    },
    "okta_idp_oidc": IDP_BASE_CONFIG,
    "okta_idp_saml": IDP_BASE_CONFIG,
    "okta_idp_social": IDP_BASE_CONFIG,
    "auth_servers": {
        "okta_endpoint": "/api/v1/authorizationServers",
        "attributes": [
            "id",
            "name",
            "audiences",
            "description",
            "issuerMode",
            "status",
        ],
    },
    "auth_servers_default": {
        "okta_endpoint": "/api/v1/authorizationServers/default",
        "attributes": [
            "name",
            "audiences",
            "description",
            "issuerMode",
            "status",
            "credentials",
        ],
    },
    "inline_hooks": {
        "okta_endpoint": "/api/v1/inlineHooks",
        "attributes": ["id","name", "type", "version", "channel"],
    },
    "sms_templates": {
        "okta_endpoint": "/api/v1/templates/sms",
        "attributes": ["type", "template", "translations"],
    },
    "threat_insights": {
        "okta_endpoint": "/api/v1/threats/configuration",
        "attributes": ["action", "excludeZones"],
    },
    "network_zones": {
        "okta_endpoint": "/api/v1/zones",
        "attributes": [
            "id",
            "name",
            "type",
            "asns",
            "gateways",
            "proxies",
            "ipServiceCategories",
            "locations",
            "status",
            "usage",
            "system",
            "dynamicProxyType",
        ],
    },
    "behavior": {
        "okta_endpoint": "/api/v1/behaviors",
        "attributes": ["id", "name", "type", "status", "settings"],
    },
    "okta_policy_device_assurance_android": {
        "okta_endpoint": "/api/v1/device-assurances",
        "attributes": [""],
    },
    "okta_policy_mfa": {
        "okta_endpoint": "/api/v1/policies",
        "attributes": [
            "id",
            "name",
            "description",
            "priority",
            "conditions",
            "settings",
        ],
    },
    "okta_policy_password": {
        "okta_endpoint": "/api/v1/policies",
        "attributes": [
            "id",
            "status",
            "priority",
            "name",
            "description",
            "conditions",
            "settings",
        ],
    },
    "okta_policy_profile_enrollment": {
        "okta_endpoint": "/api/v1/policies",
        "attributes": ["id", "name", "status"],
    },
    "okta_policy_profile_enrollment_apps": {
        "okta_endpoint": "/api/v1/policies/{policyProfileEnrollmentId}/app",
        "attributes": ["id"],
    },
    "okta_policy_rule_mfa": {
        "okta_endpoint": "/api/v1/policies/{policy_id}/rule",
        "attributes": [ "id","priority", "name", "actions", "conditions", "status"],
    },
    "okta_policy_rule_idp_discovery": {
        "okta_endpoint": "/api/v1/policies/{policy_id}/rules",
        "attributes": ["priority", "name", "actions", "conditions", "status"],
    },
    "okta_policy_rule_password": {
        "okta_endpoint": "/api/v1/policies/{policy_id}/rules",
        "attributes": ["id","priority", "name", "actions", "conditions", "status"],
    },
    "okta_policy_rule_profile_enrollment": {
        "okta_endpoint": "/api/v1/policies/{policy_id}/rules",
        "attributes": ["id", "actions"],
    },
    "okta_policy_sign_on": {
        "okta_endpoint": "/api/v1/policies",
        "attributes": ["id", "name", "description", "priority", "conditions", "status"],
    },
    "okta_policy_rule_signon": {
        "okta_endpoint": "/api/v1/policies/{policy_id}/rules",
        "attributes": ["id", "priority", "name", "actions", "conditions", "status"],
    },
    "okta_factors": {
        "okta_endpoint": "/api/v1/org/factors",
        "attributes": ["id", "status"],
    },
    "okta_email_notifications": {
        "okta_endpoint": "/api/internal/org/settings/security-notification-settings",
        "attributes": [
            "sendEmailForNewDeviceEnabled",
            "sendEmailForFactorEnrollmentEnabled",
            "sendEmailForFactorResetEnabled",
            "sendEmailForPasswordChangedEnabled",
            "reportSuspiciousActivityEnabled",
        ],
    },
    "okta_email_domain": {
        "okta_endpoint": "api/v1/email-domains",
        "attributes": ["id", "displayName", "domain", "userName"],
    },
    "okta_theme": {
        "okta_endpoint": "/api/v1/brands/{{brandId}}/themes",
        "attributes": [
            "id",
            "backgroundImage",
            "emailTemplateTouchPointVariant",
            "endUserDashboardTouchPointVariant",
            "errorPageTouchPointVariant",
            "favicon",
            "logo",
            "primaryColorHex",
            "primaryColorContrastHex",
            "secondaryColorContrastHex",
            "secondaryColorHex",
            "signInPageTouchPointVariant",
        ],
    },
    "okta_app_oauth": {
        "okta_endpoint": "/api/v1/apps",
        "attributes": [
            "id",
            "signOnMode",
            "label",
            "type",
            "accessibility",
            "visibility",
            "notes",
            "settings",
            "_links",
            "userNameTemplate",
            "status",
            "credentials",
        ],
    },
    "okta_app_saml": {
        "okta_endpoint": "/api/v1/apps",
        "attributes": [
            "id",
            "signOnMode",
            "label",
            "accessibility",
            "visibility",
            "notes",
            "settings",
            "signon",
            "hide",
            "userNameTemplate",
            "status",
        ],
    },
    "okta_app_group_assignments": {
        "okta_endpoint": "/api/v1/apps/{{appId}}/groups",
        "attributes": ["app_id", "group", "timeouts"],
    },
    "okta_app_policy_sign_on": {
        "okta_endpoint": "/api/v1/policies",
        "attributes": ["id", "name", "description", "priority", "catch_all"],
    },
    "okta_app_signon_policy_rule": {
        "okta_endpoint": "/api/v1/policies/{policy_id}/rules",
        "attributes": ["id","priority", "name", "actions", "conditions", "status", "type"]
    },
    "okta_app_saml_app_settings": {
        "okta_endpoint": "/api/v1/apps",
        "attributes": ["id", "settings", "signOnMode"],
    },
    "okta_app_oauth_role_assignment": {
        "okta_endpoint": "/oauth2/v1/clients/{client_id}/roles",
        "attributes": ["type", "resource_set", "role"],
    },
    "okta_admin_role_custom": {
        "okta_endpoint": "/api/v1/iam/roles",
        "attributes": ["description", "label", "permissions"],
    },
    "okta_admin_role_targets": {
        "okta_endpoint": "/api/v1/users/{user_id}/roles/{roleAssignmentId}/targets/catalog/apps",
        "attributes": ["name"],
    },
    "okta_role_subscription": {
        "okta_endpoint": "api/v1/roles/{role_type}/subscriptions",
        "attributes": ["notificationType", "status"],
    },
    "okta_link_definition": {
        "okta_endpoint": "/api/v1/meta/schemas/user/linkedObjects",
        "attributes": ["id", "primary", "associated"],
    },
    "okta_app_group_assignment": {
        "okta_endpoint": "/api/v1/apps/{appId}/groups",
        "attributes": ["app_id", "group", "timeouts"],
    },
    "okta_app_shared_credentials": {
        "okta_endpoint": "/api/v1/apps",
        "attributes": [
            "id",
            "label",
            "accessibility",
            "visibility",
            "settings",
            "notes",
            "oauthClient",
            "hide",
            "userNameTemplate",
        ],
    },
    "okta_user_group_memberships": {
        "okta_endpoint": "api/v1/users/{user_id}/groups",
        "attributes": ["id"],
    },
    "okta_app_swa": {
        "okta_endpoint": "/api/v1/apps",
        "attributes": [
            "id",
            "signOnMode",
            "label",
            "accessibility",
            "visibility",
            "settings",
            "logo",
            "hide",
            "userNameTemplate",
            "status",
        ],
    },
    "okta_domains": {
        "okta_endpoint": "/api/v1/domains",
        "attributes": ["domain", "brandId", "certificateSourceType"],
    },
    "okta_app_user": {"okta_endpoint": "/api/v1/apps", "attributes": ["id", "users"]},
    "okta_app_bookmark": {
        "okta_endpoint": "/api/v1/apps",
        "attributes": [
            "id",
            "signOnMode",
            "label",
            "accessibility",
            "visibility",
            "settings",
            "status",
        ],
    },
    "okta_app_auto_login": {
        "okta_endpoint": "/api/v1/apps",
        "attributes": [
            "id",
            "signOnMode",
            "label",
            "accessibility",
            "visibility",
            "settings",
            "status",
            "credentials",
        ],
    },
    "okta_app_basic_auth": {
        "okta_endpoint": "/api/v1/apps",
        "attributes": [
            "id",
            "signOnMode",
            "label",
            "accessibility",
            "visibility",
            "settings",
            "status",
        ],
    },
    "okta_app_secure_password_store": {
        "okta_endpoint": "/api/v1/apps",
        "attributes": [
            "id",
            "signOnMode",
            "label",
            "accessibility",
            "visibility",
            "settings",
            "status",
            "credentials",
        ],
    },
    "okta_app_three_field": {
        "okta_endpoint": "/api/v1/apps",
        "attributes": [
            "id",
            "signOnMode",
            "label",
            "accessibility",
            "visibility",
            "settings",
            "status",
            "credentials",
        ],
    },
    "okta_app_oauth_api_scope": {
        "okta_endpoint": "/api/v1/apps/{app_id}/grants",
        "attributes": ["issuer", "scopeId"],
    },
    "okta_apps_oauth_post_redirect_uri": {
        "okta_endpoint": "/api/v1/apps",
        "attributes": ["id", "settings", "signOnMode"],
    },
    "okta_apps_oauth_redirect_uri": {
        "okta_endpoint": "/api/v1/apps",
        "attributes": ["id", "settings", "signOnMode"],
    },
    "okta_captcha": {
        "okta_endpoint": "/api/v1/captchas",
        "attributes": ["name", "type", "siteKey"],
    },
    "okta_group_owners": {
        "okta_endpoint": "/api/v1/groups/{group_id}/owners",
        "attributes": [
            "id",
            "origin_id",
            "origin_type",
            "display_name",
            "resolved",
            "type",
        ],
    },
    # "email_template_settings":{
    #     "okta_endpoint": "/api/v1/brands/{brandId}/templates/email",
    #     "attributes": ["brandId", "template", "recipients"]
    # },
    # "roles": {
    #     "okta_endpoint": "/api/v1/iam/roles",
    #     "attributes": ["roles"]
    # }
    # "orgs": {
    #     "okta_endpoint": "/api/v1/org",
    #     "attributes": ["companyName", "website"]
    # }
}

ENTITY_UNIQUE_FIELDS = {
    "users": "email",
    "groups": "name",
    "group_memberships": "group_id",
    "user_types": "name",
    "brands": "name",
    "domains": "name",
    "event_hooks": "name",
    "identity_providers": "name",
    "auth_servers": "name",
    "inline_hooks": "name",
    "orgs": "company_name",
    "roles": "label",
}

ENTITY_IMPORT_MAPPING = {
        # Application Entities
        "okta_app_oauth": {
            "import_address": "module.okta_app_oauth.okta_app_oauth.app_oauth",
            "okta_id_field": "app_id",
            "terraform_key_field": "app_id"
        },
        "okta_app_saml": {
            "import_address": "module.okta_app_saml.okta_app_saml.app_saml",
            "okta_id_field": "app_id",
            "terraform_key_field": "app_id"
        },
        "okta_app_oauth_api_scope": {
            "import_address": "module.okta_app_oauth_api_scope.okta_app_oauth_api_scope.app_oauth_api_scope",
            "okta_id_field": "app_id",
            "terraform_key_field": "app_id"
        },
        "okta_app_swa": {
            "import_address": "module.okta_app_swa.okta_app_swa.app",
            "okta_id_field": "app_id",
            "terraform_key_field": "app_id"
        },
        "okta_app_bookmark": {
            "import_address": "module.okta_bookmark_app.okta_app_bookmark.app_bookmark",
            "okta_id_field": "app_id",
            "terraform_key_field": "app_id"
        },
        "okta_app_auto_login": {
            "import_address": "module.okta_app_auto_login.okta_app_auto_login.app",
            "okta_id_field": "app_id",
            "terraform_key_field": "app_id"
        },
        "okta_app_basic_auth": {
            "import_address": "module.okta_app_basic.okta_app_basic_auth.app_basic",
            "okta_id_field": "app_id",
            "terraform_key_field": "app_id"
        },
        "okta_app_three_field": {
            "import_address": "module.okta_app_three_field.okta_app_three_field.app",
            "okta_id_field": "app_id",
            "terraform_key_field": "app_id"
        },
        "okta_app_secure_password_store": {
            "import_address": "module.okta_app_secure_password_store.okta_app_secure_password_store.app",
            "okta_id_field": "app_id",
            "terraform_key_field": "app_id"
        },

        # App Assignment Entities
        "okta_app_user": {
            "import_address": "module.okta_app_user.okta_app_user.user",
            "okta_id_field": "app_id",  # Import uses "app_id/user_id" format
            "terraform_key_field": "app_id",  # But TF key is "app_id-user_id"
            "import_id_format": "{app_id}/{user_id}"  # Special format for import
        },
        "okta_app_group_assignment": {
            "import_address": "module.okta_app_group_assignment.okta_app_group_assignment.app_group_assignment",
            "okta_id_field": "app_id",
            "terraform_key_field": "app_id",
            "import_id_format": "{app_id}/{group_id}"
        },
        "okta_app_group_assignments": {
            "import_address": "module.okta_app_group_assignments.okta_app_group_assignments.app_group",
            "okta_id_field": "app_id",
            "terraform_key_field": "app_id",
            "import_id_format": "{app_id}/{group_id}"
        },

        # User & Group Entities
        "okta_user": {
            "import_address": "module.okta_user.okta_user.users",
            "okta_id_field": "user_id",
            "terraform_key_field": "user_id"
        },
        "okta_group": {
            "import_address": "module.okta_group.okta_group.groups",
            "okta_id_field": "group_id",
            "terraform_key_field": "group_id"
        },
        "okta_user_type": {
            "import_address": "module.okta_user_type.okta_user_type.user_type",
            "okta_id_field": "user_type_id",
            "terraform_key_field": "user_type_id"
        },
        "okta_group_rule": {
            "import_address": "module.okta_group_rule.okta_group_rule.group_rule",
            "okta_id_field": "rule_id",
            "terraform_key_field": "rule_id"
        },

        # Policy Entities
        "okta_policy_mfa": {
            "import_address": "module.okta_authenticators_enroll_policies.okta_policy_mfa.authenticator_enroll_policies",
            "okta_id_field": "policy_id",
            "terraform_key_field": "policy_id"
        },
        "okta_policy_password": {
            "import_address": "module.okta_password_policy.okta_policy_password.password_policy",
            "okta_id_field": "policy_id",
            "terraform_key_field": "policy_id"
        },
        "okta_policy_signon": {
            "import_address": "module.okta_global_signon_policies.okta_policy_signon.global_signon_policies",
            "okta_id_field": "policy_signon_id",
            "terraform_key_field": "policy_signon_id"
        },
        "okta_policy_profile_enrollment": {
            "import_address": "module.okta_profile_enrollment.okta_policy_profile_enrollment.profile_enrollment",
            "okta_id_field": "policy_id",
            "terraform_key_field": "policy_id"
        },
        "okta_app_signon_policy": {
            "import_address": "module.okta_app_signon_policy.okta_app_signon_policy.app_signon_policy",
            "okta_id_field": "app_policy_id",
            "terraform_key_field": "app_policy_id"
        },

        # Identity Provider Entities
        "okta_idp_oidc": {
            "import_address": "module.okta_idp_oidc.okta_idp_oidc.oidc_idp",
            "okta_id_field": "idp_id",
            "terraform_key_field": "idp_id"
        },
        "okta_idp_saml": {
            "import_address": "module.okta_idp_saml.okta_idp_saml.saml_idp",
            "okta_id_field": "idp_id",
            "terraform_key_field": "idp_id"
        },
        "okta_idp_social": {
            "import_address": "module.okta_idp_social.okta_idp_social.social_idp",
            "okta_id_field": "idp_id",
            "terraform_key_field": "idp_id"
        },

        # Other Entities
        "okta_auth_server": {
            "import_address": "module.okta_auth_server.okta_auth_server.azs_sfc",
            "okta_id_field": "auth_server_id",
            "terraform_key_field": "auth_server_id"
        },
        "okta_behavior": {
            "import_address": "module.okta_behavior.okta_behavior.behavior",
            "okta_id_field": "behavior_id",
            "terraform_key_field": "behavior_id"
        },
        "okta_brand": {
            "import_address": "module.okta_brand.okta_brand.brand",
            "okta_id_field": "brand_id",
            "terraform_key_field": "brand_id"
        },
        "okta_theme": {
            "import_address": "module.okta_theme.okta_theme.theme",
            "okta_id_field": "theme_id",
            "terraform_key_field": "theme_id"
        },
        "okta_network_zone": {
            "import_address": "module.okta_network_zone.okta_network_zone.network_zone",
            "okta_id_field": "zone_id",
            "terraform_key_field": "zone_id"
        },
        "okta_trusted_origin": {
            "import_address": "module.okta_trusted_origin.okta_trusted_origin.trusted_origins",
            "okta_id_field": "origin_id",
            "terraform_key_field": "origin_id"
        },
        "okta_authenticator": {
            "import_address": "module.okta_authenticator.okta_authenticator.authenticators",
            "okta_id_field": "authenticator_id",
            "terraform_key_field": "authenticator_id"
        },
        "okta_review": {
            "import_address": "module.okta_review.okta_review.review",
            "okta_id_field": "review_id",
            "terraform_key_field": "review_id"
        },
        "okta_principal_entitlements": {
            "import_address": "module.okta_principal_entitlements.okta_principal_entitlements.principal_entitlement",
            "okta_id_field": "principal_entitlement_id",
            "terraform_key_field": "principal_entitlement_id"
        },
        "okta_request_condition": {
            "import_address": "module.okta_request_condition.okta_request_condition.request_condition",
            "okta_id_field": "request_condition_id",
            "terraform_key_field": "request_condition_id"
        },
        "okta_request_sequence": {
            "import_address": "module.okta_request_sequence.okta_request_sequence.request_sequence",
            "okta_id_field": "id",
            "terraform_key_field": "id"
        },
        "okta_request_v2": {
            "import_address": "module.okta_request_v2.okta_request_v2.request_v2",
            "okta_id_field": "request_v2_id",
            "terraform_key_field": "request_v2_id"
        },
        "okta_catalog_entry_default": {
            "import_address": "module.okta_catalog_entry_default.okta_catalog_entry_default.catalog_entry_default",
            "okta_id_field": "entry_id",
            "terraform_key_field": "entry_id"
        },
        "okta_end_user_my_requests": {
            "import_address": "module.okta_end_user_my_requests.okta_end_user_my_requests.my_requests",
            "okta_id_field": "id",
            "terraform_key_field": "id"
        },
        "okta_entitlement_bundle": {
            "import_address": "module.okta_entitlement_bundle.okta_entitlement_bundle.bundle",
            "okta_id_field": "entitlement_bundle_id",
            "terraform_key_field": "entitlement_bundle_id"
        },
        "okta_entitlement": {
            "import_address": "module.okta_entitlement.okta_entitlement.entitlement",
            "okta_id_field": "entitlement_id",
            "terraform_key_field": "entitlement_id"
        },
        "okta_request": {
            "import_address": "module.okta_request.okta_request.request",
            "okta_id_field": "request_id",
            "terraform_key_field": "request_id"
        },
        "okta_request_settings": {
            "import_address": "module.okta_request_settings.okta_request_settings.request_settings",
            "okta_id_field": "id",
            "terraform_key_field": "resource_id"
        },
        "okta_principal_rate_limits": {
            "import_address": "module.okta_principal_rate_limits.okta_principal_rate_limits.principal_rate_limits",
            "okta_id_field": "principal_id",
            "terraform_key_field": "principal_id"
        },
        "okta_rate_limit_admin_notification_settings": {
            "import_address": "module.okta_rate_limit_admin_notification.okta_rate_limit_admin_notification_settings.admin_notification",
            "okta_id_field": "id",
            "terraform_key_field": "notifications_enabled"
        },
        "okta_rate_limit_warning_threshold_percentage": {
            "import_address": "module.okta_rate_limit_warning_threshold.okta_rate_limit_warning_threshold_percentage.warning_threshold",
            "okta_id_field": "id",
            "terraform_key_field": "warning_threshold"
        },
        "okta_domain": {
            "import_address": "module.okta_domain.okta_domain.domain",
            "okta_id_field": "domain_id",
            "terraform_key_field": "domain_id"
        },
        "okta_hook_key": {
            "import_address": "module.okta_hook_key.okta_hook_key.hook_key",
            "okta_id_field": "hook_key_id",
            "terraform_key_field": "hook_key_id"
        },
        "okta_api_token": {
            "import_address": "module.okta_api_token.okta_api_token.api_token",
            "okta_id_field": "id",
            "terraform_key_field": "id"
        },
        "okta_app_token": {
            "import_address": "module.okta_app_token.okta_app_token.app_token",
            "okta_id_field": "id",
            "terraform_key_field": "id",
            "import_id_format": "{client_id}/{id}"
        },
        "okta_app_connection": {
            "import_address": "module.okta_app_connection.okta_app_connection.app_connection",
            "okta_id_field": "id",
            "terraform_key_field": "id"
        },
        "okta_push_provider": {
            "import_address": "module.okta_push_provider.okta_push_provider.push_provider",
            "okta_id_field": "push_provider_id",
            "terraform_key_field": "push_provider_id"
        },
        "okta_api_service_integration": {
            "import_address": "module.okta_api_service_integration.okta_api_service_integration.api_service_integration",
            "okta_id_field": "api_service_integration_id",
            "terraform_key_field": "api_service_integration_id"
        },
        "okta_ui_schema": {
            "import_address": "module.okta_ui_schema.okta_ui_schema.ui_schema",
            "okta_id_field": "id",
            "terraform_key_field": "ui_schema_id"
        },
        "okta_agent_pools": {
            "import_address": "module.okta_agent_pools.okta_agent_pools.agent_pools",
            "okta_id_field": "agent_pool_id",
            "terraform_key_field": "agent_pool_id"
        },
        "okta_app_federated_claim": {
            "import_address": "module.okta_app_federated_claim.okta_app_federated_claim.app_federated_claim",
            "okta_id_field": "id",
            "terraform_key_field": "id",
            "import_id_format": "{app_id}/{id}"
        },
        "okta_user_risk": {
            "import_address": "module.okta_user_risk.okta_user_risk.user_risk",
            "okta_id_field": "id",
            "terraform_key_field": "user_id"
        },
        "okta_entity_risk_policy_rule": {
            "import_address": "module.okta_entity_risk_policy_rule.okta_entity_risk_policy_rule.entity_risk_policy_rule",
            "okta_id_field": "id",
            "terraform_key_field": "rule_id"
        },
        "okta_set_usage_as_exempt_list": {
            "import_address": "module.okta_set_usage_as_exempt_list.okta_set_usage_as_exempt_list.set_usage_as_exempt_list",
            "okta_id_field": "exempt_id",
            "terraform_key_field": "app_id"
        },
    }

ENTITY_TARGET_PREFIX_MAP = {
    # OAuth Apps
    "okta_app_oauth": [
        "module.okta_app_oauth.okta_app_oauth.app_oauth",
    ],

    # SAML Apps
    "okta_app_saml": [
        "module.okta_app_saml.okta_app_saml.app_saml",
    ],

    # SWA Apps
    "okta_app_swa": [
        "module.okta_app_swa.okta_app_swa.app",
    ],

    # Bookmark Apps
    "okta_app_bookmark": [
        "module.okta_bookmark_app.okta_app_bookmark.app_bookmark",
    ],

    # Auto Login Apps
    "okta_app_auto_login": [
        "module.okta_app_auto_login.okta_app_auto_login.app",
    ],

    # Basic Auth Apps
    "okta_app_basic_auth": [
        "module.okta_app_basic.okta_app_basic_auth.app_basic",
    ],

    # Three Field Apps
    "okta_app_three_field": [
        "module.okta_app_three_field.okta_app_three_field.app",
    ],

    # Secure Password Store Apps
    "okta_app_secure_password_store": [
        "module.okta_app_secure_password_store.okta_app_secure_password_store.app",
    ],

    # App Group Assignments
    "okta_app_group_assignments": [
        "module.okta_app_group_assignments.okta_app_group_assignments.app_group",
    ],

    "okta_app_group_assignment": [
        "module.okta_app_group_assignment.okta_app_group_assignment.app_group_assignment",
    ],

    # App Access Policy Assignment
    "okta_app_access_policy_assignment": [
        "module.okta_app_access_policy_assignment.okta_app_access_policy_assignment.assignment",
    ],

    # App OAuth API Scope
    "okta_app_oauth_api_scope": [
        "module.okta_app_oauth_api_scope.okta_app_oauth_api_scope.app_oauth_api_scope",
    ],

    # Note: okta_app_oauth_redirect_uri and okta_app_oauth_post_redirect_uri
    # should be managed directly on okta_app_oauth resource

    # App Signon Policy
    "okta_app_signon_policy": [
        "module.okta_app_signon_policy.okta_app_signon_policy.app_signon_policy",
    ],

    # App Users
    "okta_app_user": [
        "module.okta_app_user.okta_app_user.user",
    ],

    # Users & Groups
    "okta_user": [
        "module.okta_user.okta_user.users",
    ],

    "okta_group": [
        "module.okta_group.okta_group.groups",
    ],

    "okta_group_memberships": [
        "module.okta_group_memberships.okta_group_memberships.test",
    ],

    "okta_user_group_memberships": [
        "module.okta_user_group_memberships.okta_user_group_memberships.test",
    ],

    "okta_group_rule": [
        "module.okta_group_rule.okta_group_rule.group_rule",
    ],

    "okta_group_role": [
        "module.okta_group_role.okta_group_role.group_role",
    ],

    # Admin Roles
    "okta_admin_role_custom": [
        "module.okta_admin_role_custom.okta_admin_role_custom.custom_admin_roles",
    ],

    # Policies
    "okta_global_signon_policies": [
        "module.okta_global_signon_policies.okta_policy_signon.global_signon_policies",
    ],

    "okta_authenticator_enroll_policies": [
        "module.okta_authenticators_enroll_policies.okta_policy_mfa.authenticator_enroll_policies",
    ],

    "okta_policy_device_assurance_windows": [
        "module.okta_policy_device_assurance_windows.okta_policy_device_assurance_windows.windows_policy",
    ],

    "okta_policy_profile_enrollment": [
    "module.okta_policy_profile_enrollment.okta_policy_profile_enrollment.profile_enrollment"
    ],

    "okta_policy_signon": [
    "module.okta_policy_signon.okta_policy_signon.delegate_to_app_signon_policy"
    ],


    # Identity Providers
    "okta_idp_oidc": [
        "module.okta_idp_oidc.okta_idp_oidc.oidc_idp",
    ],

    "okta_idp_social": [
        "module.okta_idp_social.okta_idp_social.social_idp",
    ],

    "okta_idp_saml": [
        "module.okta_idp_saml.okta_idp_saml.saml_idp",
    ],

    "okta_idp_discovery": [
        "module.okta_idp_discovery.okta_policy_rule_idp_discovery.idp_discovery",
    ],

    # Other Resources
    "okta_behavior": [
        "module.okta_behavior.okta_behavior.behavior",
    ],

    "okta_brand": [
        "module.okta_brand.okta_brand.brand",
    ],

    "okta_theme": [
        "module.okta_theme.okta_theme.theme",
    ],

    "okta_network_zone": [
        "module.okta_network_zone.okta_network_zone.network_zone",
    ],

    "okta_inline_hook": [
        "module.okta_inline_hook.okta_inline_hook.inline_hook",
    ],

    # Email SMTP Server
    "okta_email_smtp_server": [
        "module.okta_email_smtp_server.okta_email_smtp_server.email_smtp_server",
    ],

    # Principal Rate Limits
    "okta_principal_rate_limits": [
        "module.okta_principal_rate_limits.okta_principal_rate_limits.principal_rate_limits",
    ],

    # Rate Limit Warning Threshold
    "okta_rate_limit_warning_threshold_percentage": [
        "module.okta_rate_limit_warning_threshold.okta_rate_limit_warning_threshold_percentage.warning_threshold",
    ],

    "okta_domain": [
        "module.okta_domain.okta_domain.domain",
    ],

    "okta_hook_key": [
        "module.okta_hook_key.okta_hook_key.hook_key",
    ],

    "okta_api_token": [
        "module.okta_api_token.okta_api_token.api_token",
    ],

    "okta_app_token": [
        "module.okta_app_token.okta_app_token.app_token",
    ],

    "okta_app_connection": [
        "module.okta_app_connection.okta_app_connection.app_connection",
    ],

    "okta_push_provider": [
        "module.okta_push_provider.okta_push_provider.push_provider",
    ],

    "okta_api_service_integration": [
        "module.okta_api_service_integration.okta_api_service_integration.api_service_integration",
    ],

    "okta_ui_schema": [
        "module.okta_ui_schema.okta_ui_schema.ui_schema",
    ],

    "okta_agent_pools": [
        "module.okta_agent_pools.okta_agent_pools.agent_pools",
    ],

    "okta_app_federated_claim": [
        "module.okta_app_federated_claim.okta_app_federated_claim.app_federated_claim",
    ],

    "okta_user_risk": [
        "module.okta_user_risk.okta_user_risk.user_risk",
    ],

    "okta_entity_risk_policy_rule": [
        "module.okta_entity_risk_policy_rule.okta_entity_risk_policy_rule.entity_risk_policy_rule",
    ],

    "okta_set_usage_as_exempt_list": [
        "module.okta_set_usage_as_exempt_list.okta_set_usage_as_exempt_list.set_usage_as_exempt_list",
    ],

    "okta_email_domain": [
        "module.okta_email_domain.okta_email_domain.email_domain",
    ],

    "okta_event_hook": [
        "module.okta_event_hook.okta_event_hook.event_hooks",
    ],

    "okta_template_sms" :[
        "module.okta_template_sms.okta_template_sms.sms_template",
    ],

    "okta_authenticator": [
        "module.okta_authenticator.okta_authenticator.authenticators",
    ],

    "okta_policy_device_assurance_android" :[
        "module.okta_policy_device_assurance_android.okta_policy_device_assurance_android.android_policy",
    ],

    "okta_policy_device_assurance_macos" :[
        "module.okta_policy_device_assurance_macos.okta_policy_device_assurance_macos.macos_policy",
    ],

    "okta_policy_device_assurance_ios" : [
        "module.okta_policy_device_assurance_ios.okta_policy_device_assurance_ios.ios_policy",
    ],

    "okta_trusted_origin" :[
        "module.okta_trusted_origin.okta_trusted_origin.trusted_origins",
    ],

    "okta_threat_insight_settings" :[
        "module.okta_threat_insight_settings.okta_threat_insight_settings.threat_insights",
    ],

    "okta_link_definition" :[
        "module.okta_link_definition.okta_link_definition.link_definition",
    ],

    "okta_org_configuration" :[
        "module.okta_org_configuration.okta_org_configuration.org_configuration",
    ],

    "okta_user_type" : [
        "module.okta_user_type.okta_user_type.user_type",
    ],

    "okta_user_base_schema_property" :[
        "module.okta_user_base_schema_property.okta_user_base_schema_property.user_base_schema_property",
    ],

    # Note: App user schema properties are commented out in Terraform - better managed manually
    "okta_app_user_base_schema_property" :[
        "module.okta_app_user_base_schema_property.okta_app_user_base_schema_property.app_user_base_schema_property",
    ],

    "okta_app_user_schema_property" :[
        "module.okta_app_user_schema_property.okta_app_user_schema_property.app_user_schema_property",
    ],

    "okta_review": [
        "module.okta_review.okta_review.review",
    ],

    "okta_principal_entitlements": [
        "module.okta_principal_entitlements.okta_principal_entitlements.principal_entitlement",
    ],

    "okta_request_condition": [
        "module.okta_request_condition.okta_request_condition.request_condition",
    ],

    "okta_request_sequence": [
        "module.okta_request_sequence.okta_request_sequence.request_sequence",
    ],

    "okta_request_v2": [
        "module.okta_request_v2.okta_request_v2.request_v2",
    ],

    "okta_catalog_entry_default": [
        "module.okta_catalog_entry_default.okta_catalog_entry_default.catalog_entry_default",
    ],

    "okta_end_user_my_requests": [
        "module.okta_end_user_my_requests.okta_end_user_my_requests.my_requests",
    ],

    "okta_entitlement_bundle": [
        "module.okta_entitlement_bundle.okta_entitlement_bundle.bundle",
    ],

    "okta_entitlement": [
        "module.okta_entitlement.okta_entitlement.entitlement",
    ],

    "okta_request": [
        "module.okta_request.okta_request.request",
    ],

    "okta_request_settings": [
        "module.okta_request_settings.okta_request_settings.request_settings",
    ],

    "okta_rate_limit_admin_notification_settings": [
        "module.okta_rate_limit_admin_notification.okta_rate_limit_admin_notification_settings.admin_notification",
    ],

}

EXCLUDED_OUTPUT_FIELDS = {
    "okta_policy_profile_enrollment": ["id"],
    # "okta_app_policy_sign_on" : ["id"],
    # "auth_server_policy": ["policy_id"],
    # "auth_servers": ["auth_server_id"],
    "groups": ["group_id"],
     "okta_policy_mfa": ["id"],
    "okta_policy_password": ["id"],
    # "okta_users": ["id"],
    "user_admin_roles": ["role_ids"],
    # "okta_app_oauth": ["app_id"],
    # "okta_group": ["group_id"],
    # Add more entity types as needed
}


def get_unique_field(entity_type):
    """Return the unique field for a given entity type."""
    return ENTITY_UNIQUE_FIELDS.get(entity_type, "_id")


def get_nested_value(data, attribute_path):
    """
    Retrieve a nested value from a dictionary based on a given attribute path.

    :param data: The dictionary (JSON response from Okta).
    :param attribute_path: The attribute path (e.g., "profile.firstName").
    :return: The extracted value or None if not found.
    """
    keys = attribute_path.split(".")
    for key in keys:
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return None
    return data


def extract_entity_data(entity_type, okta_data):
    """
    Generic method to extract relevant data based on entity type.

    :param entity_type: Type of entity (user, group, application)
    :param okta_data: List of JSON records from Okta API response
    :return: Extracted data list
    """
    try:
        if entity_type not in ENTITY_TYPE_MAPPING:
            return {"error": f"Invalid entity type: {entity_type}"}

        attributes = ENTITY_TYPE_MAPPING[entity_type]["attributes"]

        extracted_data = []
        for record in okta_data:
            if isinstance(record, dict) or isinstance(record, list):
                extracted_record = {
                    attr: get_nested_value(record, attr) for attr in attributes
                }
                extracted_data.append(extracted_record)
        logger.info(
            f"Extracted {len(extracted_data)} records for entity type {entity_type}"
        )
        return extracted_data

    except Exception as e:
        logger.error(f"Error extracting data for entity type {entity_type}: {e}")
        return {"error": f"Error extracting data for entity type {entity_type}: {e}"}


def clean_entity_data(entity_type, data_list):
    """
    Remove sensitive/internal fields like `id` before storing or outputting data.

    :param entity_type: The type of entity (used to look up excluded fields)
    :param data_list: List of dictionaries containing entity data
    :return: Cleaned list of dictionaries
    """
    excluded_fields = EXCLUDED_OUTPUT_FIELDS.get(entity_type, [])
    cleaned_data = []

    for record in data_list:
        cleaned_record = {
            key: value for key, value in record.items() if key not in excluded_fields
        }
        cleaned_data.append(cleaned_record)

    return cleaned_data
