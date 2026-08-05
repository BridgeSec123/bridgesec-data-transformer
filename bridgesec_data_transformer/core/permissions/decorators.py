"""Per-endpoint permission tagging for RolePermission (core/permissions/rbac_permission.py).

@require_permission("name") stamps the required permission name directly onto
a view method. The set of known names is derived from decorator usage itself
(populated as view modules import), so GET /api/permissions/ (via
get_known_permissions()) can never drift out of sync with what's actually
enforced.
"""
_KNOWN_PERMISSIONS = set()


def require_permission(name):
    _KNOWN_PERMISSIONS.add(name)

    def decorator(fn):
        fn.required_permission = name
        return fn

    return decorator


def get_known_permissions():
    return sorted(_KNOWN_PERMISSIONS)
