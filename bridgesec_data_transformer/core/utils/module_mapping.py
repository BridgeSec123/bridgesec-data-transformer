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
    # Apps module (9 entities)
    "App Oauth": "apps",
    "App SAML": "apps",
    "App SWA": "apps",
    "App Bookmark": "apps",
    "App Auto Login": "apps",
    "App Basic Auth": "apps",
    "App Browser Plugin": "apps",
    "App OIDC": "apps",
    "App WS Federation": "apps",

    # Users module (5 entities)
    "Users": "users",
    "User Types": "users",
    "User Factors": "users",
    "User Admin Roles": "users",
    "User Schemas": "users",

    # Groups module (4 entities)
    "Groups": "groups",
    "Group Rules": "groups",
    "Group Roles": "groups",
    "Group Schemas": "groups",

    # Policies module (4 entities)
    "Policy MFA": "policies",
    "Policy Password": "policies",
    "Policy SignOn": "policies",
    "Policy Profile Enrollment": "policies",

    # Auth Servers module (5 entities)
    "Auth Servers": "auth_servers",
    "Auth Server Scopes": "auth_servers",
    "Auth Server Claims": "auth_servers",
    "Auth Server Policies": "auth_servers",
    "Auth Server Policy Rules": "auth_servers",

    # IDPs module (3 entities)
    "IDP OIDC": "idps",
    "IDP SAML": "idps",
    "IDP Social": "idps",

    # Security module (6 entities)
    "Authenticators": "security",
    "Brands": "security",
    "Themes": "security",
    "Network Zones": "security",
    "Trusted Origins": "security",
    "Behaviors": "security",

    # Admin module (7+ entities)
    "Admin Roles": "admin",
    "Rate Limits": "admin",
    "Email Configuration": "admin",
    "Captchas": "admin",
    "Links": "admin",
    "Entitlements": "admin",
    "Catalogs": "admin",
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
