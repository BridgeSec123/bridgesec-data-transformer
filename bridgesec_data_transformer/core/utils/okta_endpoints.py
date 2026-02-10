"""
Generic mapping of entity types to Okta API endpoints.
Used for verification and deletion operations across ALL entity types.

This module provides a single source of truth for Okta API endpoints,
enabling generic operations without entity-specific code.
"""

import re
import logging

logger = logging.getLogger(__name__)

# Map entity type → Okta API endpoint pattern
# Placeholders in {braces} will be replaced with actual IDs
ENTITY_API_ENDPOINTS = {
    # ============================================
    # APPLICATIONS
    # ============================================
    "App Oauth": "/api/v1/apps/{id}",
    "App Saml": "/api/v1/apps/{id}",
    "App Swa": "/api/v1/apps/{id}",
    "App Bookmark": "/api/v1/apps/{id}",
    "App Auto Login": "/api/v1/apps/{id}",
    "App Basic Auth": "/api/v1/apps/{id}",
    "App Three Field": "/api/v1/apps/{id}",
    "App Secure Password Store": "/api/v1/apps/{id}",

    # Terraform resource names (alternate keys)
    "okta_app_oauth": "/api/v1/apps/{id}",
    "okta_app_saml": "/api/v1/apps/{id}",
    "okta_app_swa": "/api/v1/apps/{id}",
    "okta_app_bookmark": "/api/v1/apps/{id}",
    "okta_app_auto_login": "/api/v1/apps/{id}",
    "okta_app_basic_auth": "/api/v1/apps/{id}",
    "okta_app_three_field": "/api/v1/apps/{id}",
    "okta_app_secure_password_store": "/api/v1/apps/{id}",

    # App dependencies (check if parent app exists)
    "App Group Assignment": "/api/v1/apps/{app_id}",
    "App User": "/api/v1/apps/{app_id}",
    "App Access Policy Assignment": "/api/v1/apps/{app_id}",
    "App Oauth Api Scope": "/api/v1/apps/{app_id}",
    "App Oauth Redirect Uri": "/api/v1/apps/{app_id}",
    "APP Oauth Post Logout Redirect Uri": "/api/v1/apps/{app_id}",

    "okta_app_group_assignment": "/api/v1/apps/{app_id}",
    "okta_app_user": "/api/v1/apps/{app_id}",
    "okta_app_access_policy_assignment": "/api/v1/apps/{app_id}",
    "okta_app_oauth_api_scope": "/api/v1/apps/{app_id}",
    "okta_app_oauth_redirect_uri": "/api/v1/apps/{app_id}",
    "okta_app_oauth_post_logout_redirect_uri": "/api/v1/apps/{app_id}",

    # ============================================
    # GROUPS
    # ============================================
    "Groups": "/api/v1/groups/{id}",
    "Group Rules": "/api/v1/groups/rules/{id}",
    "Group Roles": "/api/v1/groups/{group_id}/roles/{id}",
    "Group Schemas": "/api/v1/meta/schemas/group/default",

    "okta_group": "/api/v1/groups/{id}",
    "okta_group_rule": "/api/v1/groups/rules/{id}",
    "okta_group_role": "/api/v1/groups/{group_id}/roles/{id}",
    "okta_group_schema": "/api/v1/meta/schemas/group/default",

    # ============================================
    # USERS
    # ============================================
    "Users": "/api/v1/users/{id}",
    "User": "/api/v1/users/{id}",
    "User Types": "/api/v1/meta/types/user/{id}",
    "User Type": "/api/v1/meta/types/user/{id}",
    "User Factors": "/api/v1/users/{user_id}/factors/{id}",
    "User Admin Roles": "/api/v1/users/{user_id}/roles/{id}",
    "User Schemas": "/api/v1/meta/schemas/user/default",

    "okta_user": "/api/v1/users/{id}",
    "okta_user_type": "/api/v1/meta/types/user/{id}",
    "okta_user_factor": "/api/v1/users/{user_id}/factors/{id}",
    "okta_user_admin_role": "/api/v1/users/{user_id}/roles/{id}",
    "okta_user_schema": "/api/v1/meta/schemas/user/default",

    # ============================================
    # POLICIES
    # ============================================
    "Policy MFA": "/api/v1/policies/{id}",
    "Policy Password": "/api/v1/policies/{id}",
    "Policy Sign On": "/api/v1/policies/{id}",
    "Policy Profile Enrollment": "/api/v1/policies/{id}",
    "Policy Rule Mfa": "/api/v1/policies/{policy_id}/rules/{id}",
    "Policy Rule Password": "/api/v1/policies/{policy_id}/rules/{id}",
    "Policy Rule Sign On": "/api/v1/policies/{policy_id}/rules/{id}",
    "Policy Rule Profile Enrollment": "/api/v1/policies/{policy_id}/rules/{id}",
    "Policy Rule Idp Discovery": "/api/v1/policies/{policy_id}/rules/{id}",

    "okta_policy_mfa": "/api/v1/policies/{id}",
    "okta_policy_password": "/api/v1/policies/{id}",
    "okta_policy_signon": "/api/v1/policies/{id}",
    "okta_policy_profile_enrollment": "/api/v1/policies/{id}",
    "okta_policy_rule_mfa": "/api/v1/policies/{policy_id}/rules/{id}",
    "okta_policy_rule_password": "/api/v1/policies/{policy_id}/rules/{id}",
    "okta_policy_rule_signon": "/api/v1/policies/{policy_id}/rules/{id}",
    "okta_policy_rule_profile_enrollment": "/api/v1/policies/{policy_id}/rules/{id}",
    "okta_policy_rule_idp_discovery": "/api/v1/policies/{policy_id}/rules/{id}",

    # ============================================
    # AUTHORIZATION SERVERS
    # ============================================
    "Auth Server": "/api/v1/authorizationServers/{id}",
    "Auth Servers": "/api/v1/authorizationServers/{id}",
    "Auth Server Scopes": "/api/v1/authorizationServers/{auth_server_id}/scopes/{id}",
    "Auth Server Claims": "/api/v1/authorizationServers/{auth_server_id}/claims/{id}",
    "Auth Server Policies": "/api/v1/authorizationServers/{auth_server_id}/policies/{id}",
    "Auth Server Policy Rules": "/api/v1/authorizationServers/{auth_server_id}/policies/{policy_id}/rules/{id}",

    "okta_auth_server": "/api/v1/authorizationServers/{id}",
    "okta_auth_server_scope": "/api/v1/authorizationServers/{auth_server_id}/scopes/{id}",
    "okta_auth_server_claim": "/api/v1/authorizationServers/{auth_server_id}/claims/{id}",
    "okta_auth_server_policy": "/api/v1/authorizationServers/{auth_server_id}/policies/{id}",
    "okta_auth_server_policy_rule": "/api/v1/authorizationServers/{auth_server_id}/policies/{policy_id}/rules/{id}",
    "okta_trusted_server": "/api/v1/authorizationServers/{id}",

    # ============================================
    # IDENTITY PROVIDERS
    # ============================================
    "IDP OIDC": "/api/v1/idps/{id}",
    "IDP SAML": "/api/v1/idps/{id}",
    "IDP SOCIAL": "/api/v1/idps/{id}",

    "okta_idp_oidc": "/api/v1/idps/{id}",
    "okta_idp_saml": "/api/v1/idps/{id}",
    "okta_idp_social": "/api/v1/idps/{id}",

    # ============================================
    # SECURITY
    # ============================================
    "Authenticators": "/api/v1/authenticators/{id}",
    "Authenticator": "/api/v1/authenticators/{id}",
    "Brands": "/api/v1/brands/{id}",
    "Brand": "/api/v1/brands/{id}",
    "Themes": "/api/v1/brands/{brand_id}/themes/{id}",
    "Theme": "/api/v1/brands/{brand_id}/themes/{id}",
    "Email Domain": "/api/v1/email-domains/{id}",
    "Network Zones": "/api/v1/zones/{id}",
    "Network Zone": "/api/v1/zones/{id}",
    "Trusted Origins": "/api/v1/trustedOrigins/{id}",
    "Trusted Origin": "/api/v1/trustedOrigins/{id}",
    "Behaviors": "/api/v1/behaviors/{id}",
    "Behavior": "/api/v1/behaviors/{id}",

    "okta_authenticator": "/api/v1/authenticators/{id}",
    "okta_brand": "/api/v1/brands/{id}",
    "okta_theme": "/api/v1/brands/{brand_id}/themes/{id}",
    "okta_email_domain": "/api/v1/email-domains/{id}",
    "okta_network_zone": "/api/v1/zones/{id}",
    "okta_trusted_origin": "/api/v1/trustedOrigins/{id}",
    "okta_behavior": "/api/v1/behaviors/{id}",

    # ============================================
    # ADMINISTRATION
    # ============================================
    "Admin Role Custom": "/api/v1/iam/roles/{id}",
    "Rate Limits": "/api/v1/rate-limit-settings/rate-limits/{id}",
    "Email SMTP Server": "/api/v1/org/email/smtp",

    "okta_admin_role_custom": "/api/v1/iam/roles/{id}",
    "okta_rate_limit": "/api/v1/rate-limit-settings/rate-limits/{id}",
    "okta_email_smtp_server": "/api/v1/org/email/smtp",
}


def get_okta_api_endpoint(entity_type: str, **id_params) -> str:
    """
    Get Okta API endpoint for an entity type with ID parameters.

    Args:
        entity_type: Entity type (e.g., "okta_app_oauth", "App Oauth")
        **id_params: ID parameters to fill in endpoint
                    (e.g., id="0oa123", policy_id="00p456")

    Returns:
        Full Okta API endpoint path

    Examples:
        >>> get_okta_api_endpoint("okta_app_oauth", id="0oa123")
        "/api/v1/apps/0oa123"

        >>> get_okta_api_endpoint("okta_policy_rule_mfa", policy_id="00p123", id="0pr456")
        "/api/v1/policies/00p123/rules/0pr456"

        >>> get_okta_api_endpoint("Auth Server", id="aus123")
        "/api/v1/authorizationServers/aus123"

    Raises:
        ValueError: If entity_type not found or required ID parameter missing
    """
    endpoint_template = ENTITY_API_ENDPOINTS.get(entity_type)

    if not endpoint_template:
        raise ValueError(
            f"Unknown entity type: '{entity_type}'. "
            f"Please add mapping to ENTITY_API_ENDPOINTS in okta_endpoints.py"
        )

    try:
        # Replace placeholders with actual IDs
        endpoint = endpoint_template.format(**id_params)
        return endpoint
    except KeyError as e:
        # Missing required parameter
        required_params = get_id_fields_for_entity(entity_type)
        raise ValueError(
            f"Missing required ID parameter {e} for entity '{entity_type}'. "
            f"Required parameters: {required_params}. "
            f"Provided: {list(id_params.keys())}"
        )


def get_id_fields_for_entity(entity_type: str) -> list:
    """
    Get list of ID fields needed for this entity type.

    Args:
        entity_type: Entity type (e.g., "okta_app_oauth")

    Returns:
        List of ID field names required for endpoint

    Examples:
        >>> get_id_fields_for_entity("okta_app_oauth")
        ['id']

        >>> get_id_fields_for_entity("okta_policy_rule_mfa")
        ['policy_id', 'id']

        >>> get_id_fields_for_entity("okta_auth_server_scope")
        ['auth_server_id', 'id']
    """
    endpoint_template = ENTITY_API_ENDPOINTS.get(entity_type, "")

    if not endpoint_template:
        logger.warning(f"No endpoint template found for entity type: {entity_type}")
        return []

    # Extract placeholder names from template
    # E.g., "/api/v1/policies/{policy_id}/rules/{id}" → ["policy_id", "id"]
    placeholders = re.findall(r'\{(\w+)\}', endpoint_template)

    return placeholders


def validate_id_params(entity_type: str, id_params: dict) -> tuple:
    """
    Validate that all required ID parameters are provided.

    Args:
        entity_type: Entity type
        id_params: Dict of ID parameters

    Returns:
        Tuple (is_valid: bool, missing_fields: list)

    Example:
        >>> validate_id_params("okta_policy_rule_mfa", {"policy_id": "00p123"})
        (False, ['id'])

        >>> validate_id_params("okta_policy_rule_mfa", {"policy_id": "00p123", "id": "0pr456"})
        (True, [])
    """
    required_fields = get_id_fields_for_entity(entity_type)
    provided_fields = set(id_params.keys())
    missing_fields = [field for field in required_fields if field not in provided_fields]

    is_valid = len(missing_fields) == 0

    return is_valid, missing_fields


def get_entity_display_name(entity_type: str) -> str:
    """
    Get human-readable display name for entity type.

    Args:
        entity_type: Entity type

    Returns:
        Display name string

    Example:
        >>> get_entity_display_name("okta_app_oauth")
        "OAuth Application"

        >>> get_entity_display_name("okta_policy_mfa")
        "MFA Policy"
    """
    display_names = {
        "okta_app_oauth": "OAuth Application",
        "okta_app_saml": "SAML Application",
        "okta_app_swa": "SWA Application",
        "okta_policy_mfa": "MFA Policy",
        "okta_policy_password": "Password Policy",
        "okta_policy_signon": "Sign-On Policy",
        "okta_auth_server": "Authorization Server",
        "okta_group": "Group",
        "okta_user": "User",
        # Add more as needed
    }

    return display_names.get(entity_type, entity_type.replace("okta_", "").replace("_", " ").title())


# Convenience function for common ID parameter extraction
def extract_id_params_from_record(entity_type: str, record: dict) -> dict:
    """
    Extract ID parameters from a record based on entity type.

    Attempts to intelligently map record fields to required ID parameters.

    Args:
        entity_type: Entity type
        record: Dict containing entity data

    Returns:
        Dict of ID parameters suitable for get_okta_api_endpoint()

    Example:
        >>> record = {"app_id": "0oa123", "label": "My App"}
        >>> extract_id_params_from_record("okta_app_oauth", record)
        {"id": "0oa123"}

        >>> record = {"policy_id": "00p123", "rule_id": "0pr456"}
        >>> extract_id_params_from_record("okta_policy_rule_mfa", record)
        {"policy_id": "00p123", "id": "0pr456"}
    """
    from core.utils.collection_mapping import ENTITY_ID_MAPPING

    required_fields = get_id_fields_for_entity(entity_type)
    id_params = {}

    for field in required_fields:
        # Try direct field name first
        if field in record and record[field]:
            id_params[field] = record[field]
            continue

        # Try entity-specific ID field mapping
        if field == "id":
            # For "id" field, try to get from ENTITY_ID_MAPPING
            entity_id_field = ENTITY_ID_MAPPING.get(entity_type)
            if entity_id_field and entity_id_field in record:
                id_params["id"] = record[entity_id_field]
                continue

        # Try common variations
        variations = [
            field,
            f"{field}_id" if not field.endswith("_id") else field[:-3],
            field.replace("_", ""),
        ]

        for variation in variations:
            if variation in record and record[variation]:
                id_params[field] = record[variation]
                break

    return id_params
