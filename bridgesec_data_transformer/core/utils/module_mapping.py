"""
Maps entity names to their respective module APIs in Terraform repo.
This enables module-based routing instead of single API endpoint.
"""

MODULE_APIS = {
    "apps": "/api/apps/",
    "users": "/api/users/",
    "groups": "/api/groups/",
    "policies": "/api/policies/",
    "auth_servers": "/api/auth-servers/",
    "idps": "/api/idps/",
    "security": "/api/security/",
    "admin": "/api/admin/",
}

ENTITY_TO_MODULE = {
    # Apps module (11+ entities)
    "App Oauth": "apps",
    "App SAML": "apps",
    "App SWA": "apps",
    "App Bookmark": "apps",
    "App Auto Login": "apps",
    "App Basic Auth": "apps",
    "App Browser Plugin": "apps",
    "App OIDC": "apps",
    "App WS Federation": "apps",
    "App Signon Policy": "apps",
    "App Signon Policy Rule": "apps",
    "App Group Assignments": "apps",
    "App Group Assignment": "apps",
    "App Access Policy Assignment": "apps",
    "App Three Field": "apps",
    "App Secure Password Store": "apps",
    "App User Schema Property": "apps",
    "App User Base Schema Property": "apps",
    "App Saml": "apps",
    "App User": "apps",
    "App Oauth Api Scope": "apps",
    "App Oauth Redirect Uri": "apps",
    "APP Oauth Post Logout Redirect Uri": "apps",

    # Users module (10+ entities)
    "Users": "users",
    "User": "users",
    "User Types": "users",
    "User Type": "users",
    "User Factors": "users",
    "User Admin Roles": "users",
    "User Schemas": "users",
    "User Schema Properties": "users",
    "User Group Memberships": "users",
    "User Base Schema Properties": "users",

    # Groups module (6+ entities)
    "Groups": "groups",
    "Group Rules": "groups",
    "Group Roles": "groups",
    "Group Schemas": "groups",
    "Group Schema Property": "groups",
    "Group Memberships": "groups",
    "Group Role": "groups",

    # Policies module (10+ entities)
    "Policy MFA": "policies",
    "Policy Password": "policies",
    "Policy SignOn": "policies",
    "Policy Sign On": "policies",
    "Policy Profile Enrollment": "policies",
    "Policy Profile Enrollment apps": "policies",
    "Policy Rule Mfa": "policies",
    "Policy Rule Password": "policies",
    "Policy Rule Sign On": "policies",
    "Policy Rule Profile Enrollment": "policies",
    "Policy Rule Idp Discovery": "policies",
    "Policy Device Assurance Android": "policies",
    "Policy Device Assurance IOS": "policies",
    "Policy Device Assurance Macos": "policies",
    "Policy Device Assurance Windows": "policies",

    # Auth Servers module (5+ entities)
    "Auth Servers": "auth_servers",
    "Auth Server": "auth_servers",
    "Auth Server Scopes": "auth_servers",
    "Auth Server Claims": "auth_servers",
    "Auth Server Policies": "auth_servers",
    "Auth Server Policy Rules": "auth_servers",

    # IDPs module (3 entities)
    "IDP OIDC": "idps",
    "IDP SAML": "idps",
    "IDP SOCIAL": "idps",

    # Security module (15+ entities)
    "Authenticators": "security",
    "Authenticator": "security",
    "Brands": "security",
    "Brand": "security",
    "Themes": "security",
    "Theme": "security",
    "Email Domain": "security",
    "Network Zones": "security",
    "Network Zone": "security",
    "Trusted Origins": "security",
    "Trusted Origin": "security",
    "Behaviors": "security",
    "Behavior": "security",
    "Threat Insights": "security",
    "Organization Security": "security",

    # Admin module (25+ entities)
    "Admin Roles": "admin",
    "Admin Role Custom": "admin",
    "Rate Limits": "admin",
    "Principal Rate Limit": "admin",
    "Rate Limit Admin Notification": "admin",
    "Rate Limit Admin Notification Settings": "admin",
    "Rate Limit Warning Threshold Percentage": "admin",
    "Email Configuration": "admin",
    "Email": "admin",
    "Email SMTP Server": "admin",
    "Captchas": "admin",
    "Links": "admin",
    "Link": "admin",
    "Link Definition": "admin",
    "Entitlements": "admin",
    "Entitlement Bundle": "admin",
    "Principal Entitlement": "admin",
    "Catalogs": "admin",
    "Sms Template": "admin",
    "Requests": "admin",
    "Request Condition": "admin",
    "Request Sequence": "admin",
    "Request Settings": "admin",
    "Inline Hooks": "admin",
    "Inline Hook": "admin",
    "Event_Hook": "admin",
    "Event Hook": "admin",
}


def get_terraform_api_for_entity(entity_name):
    """
    Get Terraform module API endpoint for a given entity name.

    Args:
        entity_name: Entity name (e.g., "App OAuth", "Users", "Policy MFA")

    Returns:
        str: API endpoint path (e.g., "/api/apps/")
        None: If entity not found

    Example:
        >>> get_terraform_api_for_entity("App OAuth")
        '/api/apps/'
        >>> get_terraform_api_for_entity("Users")
        '/api/users/'
        >>> get_terraform_api_for_entity("Policy MFA")
        '/api/policies/'
    """
    module = ENTITY_TO_MODULE.get(entity_name)
    if module:
        return MODULE_APIS.get(module)
    return None


def get_module_name(entity_name):
    """
    Get module name for entity.

    Args:
        entity_name: Entity name

    Returns:
        str: Module name (e.g., "apps", "users", "policies")
        None: If entity not found
    """
    return ENTITY_TO_MODULE.get(entity_name)


def get_all_entities_for_module(module_name):
    """
    Get all entity names belonging to a module.

    Args:
        module_name: Module name (e.g., "apps", "users")

    Returns:
        list: List of entity names in the module
    """
    return [entity for entity, mod in ENTITY_TO_MODULE.items() if mod == module_name]
