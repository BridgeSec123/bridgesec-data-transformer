"""Global RBAC gate — the single authorization authority for the API.

RolePermission checks each request's role(s) against permissions stored on
the Supabase `roles` table (see core/permissions/role_permissions.py), keyed
by a permission name every endpoint declares via
core/permissions/decorators.py:require_permission. RBAC is mandatory — there
is no enable/disable flag.

OPAPermission is unrelated to the role/permission gate: it enforces
user-authored PolicyRule deny rules (created via /api/policies/, pushed to a
live OPA instance). It runs after the role gate in DEFAULT_PERMISSION_CLASSES
so it can only add restrictions on top of an already-granted request, never
bypass it.
"""
import logging

from django.conf import settings
from rest_framework.permissions import BasePermission

from core.permissions.role_permissions import get_permissions_for_roles
from core.services import opa_client

logger = logging.getLogger(__name__)


def build_opa_input(request, entity, action, resource_id=None, resource_attributes=None):
    """Shape the OPA `input` for the deny-veto. Shared by RolePermission-adjacent
    callers and the custom restore/delete flow so both speak the same input schema.

    resource_id / resource_attributes are only present once a specific record is in
    hand (detail routes, per-record restore/delete loops); when absent, data-specific
    deny rules simply don't match — coarse user/role/action rules still fire.
    """
    user = getattr(request, "user", None)
    roles = getattr(user, "roles", None) or ([user.role] if getattr(user, "role", None) else [])
    return {
        "user": {
            "email": getattr(user, "email", None),
            "username": getattr(user, "username", None),
            "roles": roles,
            "tenant_id": str(getattr(request, "_tenant_id", None)
                             or getattr(user, "tenant_id", "") or "") or None,
        },
        "entity": entity,
        "action": action,
        "resource_id": resource_id,
        "resource_attributes": resource_attributes or {},
    }


def opa_denies(request, entity, action, resource_id=None, resource_attributes=None) -> bool:
    """True if OPA vetoes this request. No-op (False) when OPA is disabled."""
    if not getattr(settings, "OPA_ENABLED", True):
        return False
    return opa_client.query_denied(
        build_opa_input(request, entity, action, resource_id, resource_attributes)
    )


# Paths exempt from the role gate (still require authentication unless pre-auth).
# Two kinds:
#   - pre-auth / public: login, token issue/refresh, tenant resolution.
#   - self-service / own-data: authorization is "admin OR owner" / per-user and
#     is enforced inside the view, so role is not the gate here.
RBAC_BYPASS_PATHS = (
    # pre-auth / public
    "/okta/login/",
    "/okta/callback/",
    "/okta/logout/",
    "/api/token/",
    "/api/token/refresh/",
    "/api/auth/token/",
    "/api/auth/resolve-tenant/",
    "/api/auth/me/",
    "/api/auth/my-tenants/",
    # self-service / own-data (in-view ownership checks)
    "/api/users/",
    "/api/roles/",
    "/api/policies/",
    "/api/notifications/",
    "/api/permissions/",
)


METHOD_TO_ACTION = {
    "GET": "read",
    "HEAD": "read",
    "OPTIONS": "read",
    "POST": "create",
    "PUT": "update",
    "PATCH": "update",
    "DELETE": "delete",
}

OPERATION_TYPE_TO_ACTION = {
    "delete": "delete",
    "restore": "update",
    "create": "create",
}


class RolePermission(BasePermission):
    """DRF permission gating every request against roles.permissions in Supabase."""

    message = "You do not have permission to perform this action."

    def has_permission(self, request, view) -> bool:
        path = request.path
        if any(path.startswith(p) for p in RBAC_BYPASS_PATHS):
            return True
        if not getattr(request.user, "is_authenticated", False):
            return False
        # Views managing their own per-tenant/ownership authorization opt out of
        # the role gate (e.g. tenant logo, which lives under /api/tenants/ but is
        # not super-admin-only).
        if getattr(view, "rbac_exempt", False):
            return True

        handler_name = getattr(view, "action", None) or (request.method or "").lower()
        handler = getattr(view, handler_name, None)
        required = getattr(handler, "required_permission", None)
        if required is None:
            return False  # undecorated endpoint = deny, not open by accident

        roles = getattr(request.user, "roles", None) or []
        return required in get_permissions_for_roles(roles)


class OPAPermission(BasePermission):
    """Fine-grained OPA deny-veto for user-authored PolicyRule rules. Ordered
    after RolePermission in DEFAULT_PERMISSION_CLASSES so it only ever runs
    once the role gate has already granted the request — it can only add
    restrictions on top of that grant, never bypass it."""

    message = "Policy denies this action."

    def has_permission(self, request, view) -> bool:
        path = request.path
        if any(path.startswith(p) for p in RBAC_BYPASS_PATHS):
            return True
        if not getattr(request.user, "is_authenticated", False):
            return False
        if getattr(view, "rbac_exempt", False):
            return True
        entity = _resolve_entity(request, view)
        action = _resolve_action(request)
        # No record here, so only user/role/action-level denies fire; data-specific
        # denies wait for the object (has_object_permission) or the restore/delete
        # per-record loop.
        return not opa_denies(request, entity, action)

    def has_object_permission(self, request, view, obj) -> bool:
        if not self.has_permission(request, view):
            return False
        entity = _resolve_entity(request, view)
        action = _resolve_action(request)
        if isinstance(obj, dict):
            resource_id = obj.get("id") or obj.get("_id")
            attrs = obj
        else:
            resource_id = getattr(obj, "id", None)
            attrs = getattr(obj, "__dict__", {})
        return not opa_denies(request, entity, action, resource_id=resource_id, resource_attributes=attrs)


def _resolve_action(request) -> str:
    operation_type = request.query_params.get("operation_type", "").lower()
    if operation_type in OPERATION_TYPE_TO_ACTION:
        return OPERATION_TYPE_TO_ACTION[operation_type]
    # confirm-delete endpoint: action=confirm means a delete is executing
    if request.query_params.get("action", "").lower() == "confirm":
        return "delete"
    return METHOD_TO_ACTION.get((request.method or "GET").upper(), "read")


# Path -> entity, for OPA input on views that have no `entity_type` (e.g. plain
# config APIViews). Small and static enough to inline here directly rather than
# depend on a parsed file — previously permissions.ini's [paths] section.
_PATH_ENTITY_MAP = {
    "/api/scheduler-config/": "scheduler_config",
    "/api/entity-config/": "entity_config",
}


def _resolve_entity(request, view):
    # Restore endpoint carries entity_name in URL kwargs — prefer it.
    kwargs = getattr(view, "kwargs", {}) or {}
    if kwargs.get("entity_name"):
        return kwargs["entity_name"]
    if getattr(view, "entity_type", None):
        return view.entity_type
    for prefix, entity in _PATH_ENTITY_MAP.items():
        if request.path.startswith(prefix):
            return entity
    return None
