import logging

from django.conf import settings
from rest_framework.permissions import BasePermission

from core.services import opa_client
from core.utils.mongo_utils import get_dynamic_db

logger = logging.getLogger(__name__)


# Paths that short-circuit OPA evaluation entirely (no OPA call).
# These are auth/policy-management/self-service routes that would either
# cause bootstrap loops or need to run before any policy can apply.
OPA_BYPASS_PATHS = (
    "/okta/login/",
    "/okta/callback/",
    "/okta/logout/",
    "/api/token/",
    "/api/token/refresh/",
    "/api/auth/token/",
    "/api/auth/me/",           # self-service: reads caller's own context
    "/api/auth/my-tenants/",   # self-service: reads caller's own memberships
    "/api/policies/",
    "/api/users/",
    "/api/roles/",
    "/api/entity-config/",        # has its own EntityConfigPermission
    "/api/scheduler-config/",     # has its own inline permission check
    "/api/cross-tenant-migrate/", # has its own inline super-admin check
)


# Whitelist of scalar fields safe to expose to OPA from a MongoEngine document.
# Extend this list as new field_conditions are added to policies.
RESOURCE_ATTRIBUTE_FIELDS = (
    "created_by",
    "status",
    "label",
    "name",
    "type",
    "last_updated",
    "created",
    "tenant_id",
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


class OPAPermission(BasePermission):
    """DRF permission that consults OPA for every request.

    - Bypass paths short-circuit to True (self-management / auth).
    - If OPA_ENABLED is False, always allows (dev escape hatch).
    - Unauthenticated requests are denied here (defense in depth).
    - Otherwise, the request is described in a structured input dict and
      posted to OPA's /v1/data/authz/allow. On any error: fail-closed (403).
    """

    message = "You do not have permission to perform this action."

    # ------------------------------------------------------------------
    # DRF hooks
    # ------------------------------------------------------------------
    def has_permission(self, request, view) -> bool:
        if any(request.path.startswith(p) for p in OPA_BYPASS_PATHS):
            return True
        if not getattr(settings, "OPA_ENABLED", True):
            return True
        if not getattr(request.user, "is_authenticated", False):
            return False
        # super_admin bypasses OPA at the Django layer — works even when OPA is down
        if "super_admin" in (getattr(request.user, "roles", None) or []):
            return True
        return opa_client.query(self._build_base_input(request, view))

    def has_object_permission(self, request, view, obj) -> bool:
        if any(request.path.startswith(p) for p in OPA_BYPASS_PATHS):
            return True
        if not getattr(settings, "OPA_ENABLED", True):
            return True
        if not getattr(request.user, "is_authenticated", False):
            return False
        # super_admin bypasses OPA at the Django layer
        if "super_admin" in (getattr(request.user, "roles", None) or []):
            return True

        input_data = self._build_base_input(request, view)
        input_data["resource_attributes"] = self._extract_resource_attributes(obj)
        return opa_client.query(input_data)

    # ------------------------------------------------------------------
    # Input construction helpers
    # ------------------------------------------------------------------
    OPERATION_TYPE_TO_ACTION = {
        "delete":  "delete",
        "restore": "update",
        "create":  "create",
    }

    def _action_from_method(self, method: str) -> str:
        return METHOD_TO_ACTION.get((method or "GET").upper(), "read")

    def _resolve_action(self, request, view) -> str:
        operation_type = request.query_params.get("operation_type", "").lower()
        if operation_type in self.OPERATION_TYPE_TO_ACTION:
            return self.OPERATION_TYPE_TO_ACTION[operation_type]
        # confirm-delete endpoint: action=confirm means delete is executing
        if request.query_params.get("action", "").lower() == "confirm":
            return "delete"
        return self._action_from_method(request.method)

    def _resolve_entity(self, request, view) -> str:
        # Restore endpoint carries entity_name in URL kwargs — prefer over entity_type
        kwargs = getattr(view, "kwargs", {}) or {}
        if kwargs.get("entity_name"):
            return kwargs["entity_name"]
        return getattr(view, "entity_type", None)

    def _build_base_input(self, request, view) -> dict:
        try:
            db_prefix = getattr(request, '_db_prefix', None)
            db_name = get_dynamic_db(prefix=db_prefix)
        except Exception:
            db_name = None

        user = getattr(request, "user", None)
        # Support both legacy single-role and new multi-role
        roles = getattr(user, "roles", None) or []
        if not roles and getattr(user, "role", None):
            roles = [user.role]
        # Tenant fed to OPA is the JWT-scoped ACTIVE tenant (set by
        # CustomJWTAuthentication), not the user's global home tenant — a user can
        # belong to several tenants. Falls back to the user's home tenant when the
        # request carries no active tenant (single-tenant / legacy callers).
        active_tenant_id = getattr(request, "_tenant_id", None) or getattr(user, "tenant_id", "")
        return {
            "user": {
                "email":            getattr(user, "email", None),
                "roles":            roles,
                "tenant_id":        str(active_tenant_id or ""),
                "is_authenticated": bool(getattr(user, "is_authenticated", False)),
            },
            "method": request.method,
            "action": self._resolve_action(request, view),
            "entity": self._resolve_entity(request, view),
            "resource_id": (getattr(view, "kwargs", {}) or {}).get("pk"),
            "db_name": db_name,
            "path": request.path,
            "resource_attributes": {},
            "payload_meta": self._payload_meta(request, view),
        }

    def _payload_meta(self, request, view) -> dict:
        """Extract only metadata from the request body — never forwards large `data[]` arrays."""
        data = getattr(request, "data", None) or {}
        try:
            action_type = data.get("action") if isinstance(data, dict) else None
        except Exception:
            action_type = None

        record_count = 0
        try:
            if isinstance(data, dict) and isinstance(data.get("data"), list):
                record_count = len(data["data"])
        except Exception:
            record_count = 0

        kwargs = getattr(view, "kwargs", {}) or {}
        return {
            "action_type": action_type,
            "record_count": record_count,
            "target_db": kwargs.get("db_name"),
            "target_entity": kwargs.get("entity_name"),
        }

    def _extract_resource_attributes(self, obj) -> dict:
        """Extract a whitelisted set of scalar fields from a MongoEngine document."""
        attrs = {"id": str(getattr(obj, "pk", None))}
        for field in RESOURCE_ATTRIBUTE_FIELDS:
            val = getattr(obj, field, None)
            if val is None:
                continue
            attrs[field] = val if isinstance(val, (bool, int, float)) else str(val)

        # Optional nested extraction for profile.userType, a common Okta pattern.
        profile = getattr(obj, "profile", None)
        if isinstance(profile, dict):
            user_type = profile.get("userType")
            if user_type is not None:
                attrs["profile.userType"] = str(user_type)

        return attrs
