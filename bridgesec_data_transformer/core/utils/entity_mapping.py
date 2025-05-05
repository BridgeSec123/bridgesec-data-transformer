import logging

logger = logging.getLogger(__name__)

IDP_BASE_CONFIG = {
    "okta_endpoint": "/api/v1/idps",
    "attributes": ["name", "protocol", "policy", "type"]
}

ENTITY_TYPE_MAPPING = {
    "authenticators": {
        "okta_endpoint": "/api/v1/authenticators",
        "attributes": ["key", "name", "status", "settings"],
    },
    "trusted_origins": {
        "okta_endpoint": "/api/v1/trustedOrigins",
        "attributes": ["name", "origin", "scopes", "status"]
    },
    "users": {
        "okta_endpoint": "/api/v1/users",
        "attributes": ["id", "profile"],
    },
    "user_factors":{
        "okta_endpoint": "/api/v1/users/{userId}/factors",
        "attributes": ["id", "status"]
    },
    "user_admin_roles": {
        "okta_endpoint": "/api/v1/users/{userId}/roles",
        "attributes": ["id", "type", "disableNotifications"]
    },
    "groups": {
        "okta_endpoint": "/api/v1/groups",
        "attributes": ["id", "profile"],
    },
    "group_owners": {
        "okta_endpoint": "/api/v1/groups/{groupId}/owners",
        "attributes": ["id"]
    },
    "group_memberships": {
        "okta_endpoint": "/api/v1/groups/{groupId}/users",
        "attributes": ["id"]
    },
    "group_schemas": {
        "okta_endpoint": "/api/v1/meta/schemas/group/default",
        "attributes": ["title", "type", "definitions", "description"]
    },
    "user_types" : {
        "okta_endpoint": "/api/v1/meta/types/user",
        "attributes": ["name", "displayName", "description"]
    },
    "brands": {
        "okta_endpoint": "/api/v1/brands",
        "attributes": ["id", "name", "removePoweredByOkta", "customPrivacyPolicyUrl", "agreeToCustomPrivacyPolicy", "defaultApp", "locale"],
    },
    "domains": {
        "okta_endpoint": "/api/v1/domains",
        "attributes": ["id", "domain", "brandId", "certificateSourceType", "validationStatus"]
    },
    "event_hooks" : {
        "okta_endpoint": "/api/v1/eventHooks",
        "attributes": ["name", "events", "channel"]
    },
    "okta_idp_oidc": IDP_BASE_CONFIG,
    "okta_idp_saml": IDP_BASE_CONFIG,
    "okta_idp_social": IDP_BASE_CONFIG,
    "auth_servers": {
        "okta_endpoint": "/api/v1/authorizationServers",
        "attributes": ["id", "name", "audiences", "description", "issuerMode", "status"]
    },
    "auth_servers_default":{
        "okta_endpoint": "/api/v1/authorizationServers/default",
        "attributes": ["name", "audiences", "description", "issuerMode", "status", "credentials"]
    },
    "inline_hooks": {
        "okta_endpoint" : "/api/v1/inlineHooks",
        "attributes": ["name", "type", "version", "channel"]
    },
    "sms_templates": {
        "okta_endpoint": "/api/v1/templates/sms",
        "attributes": ["type", "template", "translations"]
    },
    "threat_insights": {
        "okta_endpoint": "/api/v1/threats/configuration",
        "attributes": ["action", "excludeZones"]
    },
    "network_zones": {
        "okta_endpoint": "/api/v1/zones",
        "attributes": ["name", "type", "asns", "gateways", "proxies", "ipServiceCategories", "locations"]
    },
    "behavior": {
        "okta_endpoint": "/api/v1/behaviors",
        "attributes": ["name", "type", "status", "velocity", "settings"]
    },
    "okta_policy_device_assurance_android": {
        "okta_endpoint": "/api/v1/device-assurances",
        "attributes": [""]
    },
    "okta_policy_mfa":{
        "okta_endpoint": "/api/v1/policies",
        "attributes": ["id", "name", "description", "priority", "conditions", "settings"]
    },
    "okta_policy_password": {
        "okta_endpoint": "/api/v1/policies",
        "attributes": ["id", "status", "priority", "name", "description", "conditions", "settings"]
    },
    "okta_policy_profile_enrollment": {
        "okta_endpoint": "/api/v1/policies",
        "attributes": ["id", "name", "status"]
    },
    "okta_policy_profile_enrollment_apps": {
        "okta_endpoint": "/api/v1/policies/{policyProfileEnrollmentId}/app",
        "attributes": ["id"]
    },
    "okta_policy_rule_mfa": {
        "okta_endpoint": "/api/v1/policies/{policy_id}/rule",
        "attributes": ["priority", "name", "actions", "conditions", "status"]
    },
    "okta_policy_rule_idp_discovery": {
        "okta_endpoint": "/api/v1/policies/{policy_id}/rules",
        "attributes": ["priority", "name", "actions", "conditions", "status"]
    },
    "okta_policy_rule_password": {
        "okta_endpoint": "/api/v1/policies/{policy_id}/rules",
        "attributes": ["priority", "name", "actions", "conditions", "status"]
    },
    "okta_policy_rule_profile_enrollment": {
        "okta_endpoint": "/api/v1/policies/{policy_id}/rules",
        "attributes": ["actions"]
    },
    "okta_policy_sign_on": {
        "okta_endpoint": "/api/v1/policies",
        "attributes": ["id", "name", "description", "priority", "conditions", "status"]
    },
    "okta_policy_rule_signon": {
        "okta_endpoint": "/api/v1/policies/{policy_id}/rules",
        "attributes": ["priority", "name", "actions", "conditions", "status"]
    },
    "okta_factors": {
        "okta_endpoint": "/api/v1/org/factors",
        "attributes": ["id", "status"]
    },
    "okta_email_notifications": {
        "okta_endpoint": "/api/internal/org/settings/security-notification-settings",
        "attributes": [
            "sendEmailForNewDeviceEnabled","sendEmailForFactorEnrollmentEnabled", "sendEmailForFactorResetEnabled", 
            "sendEmailForPasswordChangedEnabled","reportSuspiciousActivityEnabled"
        ]
    },
    "okta_email_domain": {
        "okta_endpoint": "api/v1/email-domains",
        "attributes": ["displayName", "domain", "userName"]
    },
    "okta_theme": {
        "okta_endpoint": "/api/v1/brands/{{brandId}}/themes",
        "attributes": [
            "brandid","backgroundImage","emailTemplateTouchPointVariant","endUserDashboardTouchPointVariant",
            "errorPageTouchPointVariant","favicon","logo","primaryColorHex","primaryColorContrastHex","secondaryColorContrastHex",
            "secondaryColorHex","signInPageTouchPointVariant","id"
        ]
    },
    "okta_app_oauth": {
        "okta_endpoint": "/api/v1/apps",
        "attributes": [
            "signOnMode", "label", "type", "accessibility", "visibility", "notes", "settings", "link", "userNameTemplate", "status"
        ]
    },
    "okta_app_saml": {
        "okta_endpoint": "/api/v1/apps",
        "attributes": [
            "signOnMode", "label", "accessibility", "visibility", "notes", "settings",
            "signon", "hide","userNameTemplate", "status"
            ]
    },
    "okta_apps_group_assignments": {
        "okta_endpoint": "/api/v1/apps/{{appId}}/groups",
        "attributes": [ "app_id", "group","timeouts"]
    },
    "okta_app_policy_sign_on": {
        "okta_endpoint": "/api/v1/policies",
        "attributes": ["name", "description", "priority", "catch_all"]
    },
    "okta_admin_role_custom": {
           "okta_endpoint": "/api/v1/iam/roles",
           "attributes": ["description","label", "permissions"]
    },
    "okta_admin_role_targets": {
        "okta_endpoint": "/api/v1/users/{user_id}/roles/{roleAssignmentId}/targets/catalog/apps",
        "attributes": ["name"]
    },
    "okta_role_subscription": {
        "okta_endpoint": "api/v1/roles/{role_type}/subscriptions",
        "attributes": ["notificationType","status"]
    },
    "okta_link_definition": {
        "okta_endpoint": "/api/v1/meta/schemas/user/linkedObjects",
        "attributes": ["primary","associated"]
    },
    "okta_apps_group_assignment": {
        "okta_endpoint": "/api/v1/apps/{appId}/groups",
        "attributes": [ "app_id","group","timeouts"]
    },
    "okta_app_shared_credentials":{
        "okta_endpoint": "/api/v1/apps",
        "attributes":  [
            "label", "accessibility", "visibility", "settings", "notes","oauthClient","hide","userNameTemplate"
        ]
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
    "roles": "label"
}

EXCLUDED_OUTPUT_FIELDS = {
    "okta_policy_profile_enrollment": ["id"]
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
                extracted_record = {attr: get_nested_value(record, attr) for attr in attributes}
                extracted_data.append(extracted_record)
        logger.info(f"Extracted {len(extracted_data)} records for entity type {entity_type}")
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
            key: value for key, value in record.items()
            if key not in excluded_fields
        }
        cleaned_data.append(cleaned_record)

    return cleaned_data