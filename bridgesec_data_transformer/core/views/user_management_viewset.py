import logging

from django.contrib.auth.hashers import make_password
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.authentication import CustomJWTAuthentication, _get_user_backend

logger = logging.getLogger(__name__)

_TAG = ["User Management"]

# System roles that only super_admin can assign or remove
_PRIVILEGED_ROLES = {"super_admin", "tenant_admin"}


def _serialize_user(user) -> dict:
    return {
        "id":        str(user.id),
        "email":     user.email,
        "username":  user.username,
        "roles":     getattr(user, "roles", ["user"]),
        "tenant_id": str(user.tenant_id) if getattr(user, "tenant_id", None) else None,
    }


def _serialize_user_from_junction(row, tenant_id: str) -> dict:
    """Serialize a user_tenants junction row (shape: {role, users: {id, email, username, roles}})."""
    user_data = row.get("users") or {}
    return {
        "id":          str(user_data.get("id", "")),
        "email":       user_data.get("email", ""),
        "username":    user_data.get("username", ""),
        "roles":       user_data.get("roles") or ["user"],
        "tenant_id":   tenant_id,
        "tenant_role": row.get("role", "user"),
    }


def _is_super_admin(user) -> bool:
    return "super_admin" in (getattr(user, "roles", None) or [])


def _is_tenant_admin(user) -> bool:
    roles = getattr(user, "roles", None) or []
    return "super_admin" in roles or "tenant_admin" in roles


def _require_admin(request):
    """Return a 403 Response if the caller is not tenant_admin or super_admin."""
    if not _is_tenant_admin(request.user):
        return Response(
            {"detail": "Admin access required."},
            status=status.HTTP_403_FORBIDDEN,
        )
    return None


class UserManagementViewSet(viewsets.ViewSet):
    """
    Full CRUD for application users.

    /api/users/ is in OPA_BYPASS_PATHS so OPA is skipped here.
    Admin-only enforcement is done manually in each action.

    Endpoints
    ---------
    GET    /api/users/                          — list all users (admin)
    POST   /api/users/                          — create a user (admin)
    GET    /api/users/<id>/                     — retrieve a user (admin or self)
    PATCH  /api/users/<id>/                     — update username/email (admin or self)
    DELETE /api/users/<id>/                     — delete a user (admin, not self)
    GET    /api/users/<id>/roles/               — list user roles
    PUT    /api/users/<id>/roles/               — replace user roles
    POST   /api/users/<id>/roles/add/           — append roles to user
    DELETE /api/users/<id>/roles/<role_name>/   — remove one role
    GET    /api/users/me/                       — current user profile
    """

    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    # ------------------------------------------------------------------ #
    # GET /api/users/
    # ------------------------------------------------------------------ #
    @swagger_auto_schema(
        tags=_TAG,
        operation_summary="List all users",
        manual_parameters=[
            openapi.Parameter("page",      openapi.IN_QUERY, type=openapi.TYPE_INTEGER, default=1),
            openapi.Parameter("page_size", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, default=20),
            openapi.Parameter(
                "tenant_id", openapi.IN_QUERY, type=openapi.TYPE_STRING,
                description="Super-admin only: override which tenant to list. Omit to auto-derive from JWT.",
            ),
        ],
    )
    def list(self, request):
        denied = _require_admin(request)
        if denied:
            return denied

        page      = max(1, int(request.query_params.get("page", 1)))
        page_size = min(100, max(1, int(request.query_params.get("page_size", 20))))

        # Resolve tenant_id in priority order:
        # 1. ?tenant_id= query param (super_admin only — prevents cross-tenant escalation)
        # 2. request._tenant_id from JWT claim (set by both HS256 and Okta auth paths)
        # 3. user record tenant_id (fallback for tokens issued without tenant claim)
        # 4. None → super_admin sees all users; non-admin gets 400
        tenant_id = None
        if _is_super_admin(request.user):
            tenant_id = request.query_params.get("tenant_id") or None

        if not tenant_id:
            tenant_id = getattr(request, "_tenant_id", None) or None

        if not tenant_id:
            raw = getattr(request.user, "tenant_id", None)
            tenant_id = str(raw) if raw else None

        if not tenant_id and not _is_super_admin(request.user):
            return Response(
                {"detail": "Could not determine tenant from your token. Contact an administrator."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # When scoped to a tenant, fetch from user_tenants junction table so users
        # added via tenant membership (not just users.tenant_id FK) are included.
        if tenant_id:
            from core.utils.supabase_user_tenant import SupabaseUserTenant
            rows, total = SupabaseUserTenant.get_users_for_tenant(
                tenant_id, page=page, page_size=page_size
            )
            return Response({
                "total":     total,
                "page":      page,
                "page_size": page_size,
                "tenant_id": tenant_id,
                "results":   [_serialize_user_from_junction(r, tenant_id) for r in rows],
            })

        # No tenant_id — super_admin listing all users system-wide.
        UserBackend = _get_user_backend()
        users, total = UserBackend.list_all(page=page, page_size=page_size)
        return Response({
            "total":     total,
            "page":      page,
            "page_size": page_size,
            "tenant_id": None,
            "results":   [_serialize_user(u) for u in users],
        })

    # ------------------------------------------------------------------ #
    # POST /api/users/
    # ------------------------------------------------------------------ #
    @swagger_auto_schema(
        tags=_TAG,
        operation_summary="Create a user",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email", "username"],
            properties={
                "email":     openapi.Schema(type=openapi.TYPE_STRING),
                "username":  openapi.Schema(type=openapi.TYPE_STRING),
                "password":  openapi.Schema(type=openapi.TYPE_STRING, description="Required when creating a super_admin (for /super-admin/login/)"),
                "roles":     openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING), default=["user"]),
                "tenant_id": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    def create(self, request):
        denied = _require_admin(request)
        if denied:
            return denied

        email     = (request.data.get("email") or "").strip().lower()
        username  = (request.data.get("username") or "").strip()
        roles     = request.data.get("roles") or ["user"]
        tenant_id = request.data.get("tenant_id") or None
        password  = request.data.get("password") or None

        if not email:
            raise ValidationError({"email": "This field is required."})
        if not username:
            raise ValidationError({"username": "This field is required."})
        if not isinstance(roles, list):
            raise ValidationError({"roles": "Must be a list of role names."})
        # Non-super-admin cannot assign privileged roles
        if not _is_super_admin(request.user) and any(r in _PRIVILEGED_ROLES for r in roles):
            return Response(
                {"detail": f"Only super_admin can assign privileged roles: {_PRIVILEGED_ROLES}"},
                status=status.HTTP_403_FORBIDDEN,
            )
        # Password required when creating a super_admin (needed for /super-admin/login/)
        if "super_admin" in roles and not password:
            raise ValidationError({"password": "Password is required when creating a super_admin."})
        if password and len(password) < 12:
            raise ValidationError({"password": "Password must be at least 12 characters."})

        UserBackend = _get_user_backend()
        if UserBackend.get_by_email(email):
            raise ValidationError({"email": "A user with this email already exists."})

        user = UserBackend.create_or_update(
            email=email, username=username, roles=roles, tenant_id=tenant_id,
        )

        # Store hashed password when provided (required for super_admin, optional for others)
        if password:
            from core.utils.supabase_client import get_supabase_client
            get_supabase_client().table("users").update(
                {"password": make_password(password)}
            ).eq("id", str(user.id)).execute()

        return Response(_serialize_user(user), status=status.HTTP_201_CREATED)

    # ------------------------------------------------------------------ #
    # GET /api/users/<id>/
    # ------------------------------------------------------------------ #
    @swagger_auto_schema(tags=_TAG, operation_summary="Retrieve a user")
    def retrieve(self, request, pk=None):
        user = self._get_user_or_404(pk)
        if not self._is_admin_or_self(request, user):
            return Response({"detail": "You can only view your own profile."}, status=status.HTTP_403_FORBIDDEN)
        return Response(_serialize_user(user))

    # ------------------------------------------------------------------ #
    # PATCH /api/users/<id>/
    # ------------------------------------------------------------------ #
    @swagger_auto_schema(
        tags=_TAG,
        operation_summary="Update a user's username or email",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "username": openapi.Schema(type=openapi.TYPE_STRING),
                "email":    openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    def partial_update(self, request, pk=None):
        user = self._get_user_or_404(pk)
        if not self._is_admin_or_self(request, user):
            return Response({"detail": "You can only update your own profile."}, status=status.HTTP_403_FORBIDDEN)

        new_username = request.data.get("username")
        new_email    = request.data.get("email")

        if new_username:
            user.username = new_username.strip()
        if new_email:
            new_email = new_email.strip().lower()
            UserBackend = _get_user_backend()
            existing = UserBackend.get_by_email(new_email)
            if existing and str(existing.id) != str(user.id):
                raise ValidationError({"email": "A user with this email already exists."})
            user.email = new_email

        user.save()
        return Response(_serialize_user(user))

    # ------------------------------------------------------------------ #
    # DELETE /api/users/<id>/
    # ------------------------------------------------------------------ #
    @swagger_auto_schema(tags=_TAG, operation_summary="Delete a user")
    def destroy(self, request, pk=None):
        denied = _require_admin(request)
        if denied:
            return denied

        if str(getattr(request.user, "id", "")) == str(pk):
            return Response({"detail": "You cannot delete your own account."}, status=status.HTTP_400_BAD_REQUEST)

        UserBackend = _get_user_backend()
        if not UserBackend.delete_by_id(pk):
            raise NotFound(f"User '{pk}' not found.")
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ------------------------------------------------------------------ #
    # GET/PUT /api/users/<id>/roles/
    # ------------------------------------------------------------------ #
    @swagger_auto_schema(method="get", tags=_TAG, operation_summary="Get user roles")
    @swagger_auto_schema(method="put", tags=_TAG, operation_summary="Replace user roles")
    @action(detail=True, methods=["get", "put"], url_path="roles")
    def manage_roles(self, request, pk=None):
        if request.method == "GET":
            user = self._get_user_or_404(pk)
            if not self._is_admin_or_self(request, user):
                return Response({"detail": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
            return Response({"roles": user.roles})

        # PUT — replace full roles list
        denied = _require_admin(request)
        if denied:
            return denied

        new_roles = request.data.get("roles")
        if not isinstance(new_roles, list) or not new_roles:
            raise ValidationError({"roles": "Must be a non-empty list of role names."})
        if not _is_super_admin(request.user) and any(r in _PRIVILEGED_ROLES for r in new_roles):
            return Response(
                {"detail": f"Only super_admin can assign: {_PRIVILEGED_ROLES}"},
                status=status.HTTP_403_FORBIDDEN,
            )

        user = self._get_user_or_404(pk)
        self._guard_last_super_admin(user, new_roles)
        UserBackend = _get_user_backend()
        UserBackend.update_roles(pk, new_roles)
        return Response({"id": str(user.id), "roles": new_roles})

    # ------------------------------------------------------------------ #
    # POST /api/users/<id>/roles/add/
    # ------------------------------------------------------------------ #
    @swagger_auto_schema(tags=_TAG, operation_summary="Add roles to user")
    @action(detail=True, methods=["post"], url_path="roles/add")
    def add_roles(self, request, pk=None):
        denied = _require_admin(request)
        if denied:
            return denied

        roles_to_add = request.data.get("roles") or []
        if not isinstance(roles_to_add, list):
            raise ValidationError({"roles": "Must be a list."})
        if not _is_super_admin(request.user) and any(r in _PRIVILEGED_ROLES for r in roles_to_add):
            return Response(
                {"detail": f"Only super_admin can assign: {_PRIVILEGED_ROLES}"},
                status=status.HTTP_403_FORBIDDEN,
            )

        user = self._get_user_or_404(pk)
        current = list(user.roles or ["user"])
        merged = list(dict.fromkeys(current + roles_to_add))   # preserve order, deduplicate
        UserBackend = _get_user_backend()
        UserBackend.update_roles(pk, merged)
        return Response({"id": str(user.id), "roles": merged})

    # ------------------------------------------------------------------ #
    # DELETE /api/users/<id>/roles/<role_name>/
    # ------------------------------------------------------------------ #
    @swagger_auto_schema(tags=_TAG, operation_summary="Remove a role from user")
    @action(detail=True, methods=["delete"], url_path="roles/(?P<role_name>[^/.]+)")
    def remove_role(self, request, pk=None, role_name=None):
        denied = _require_admin(request)
        if denied:
            return denied

        if not _is_super_admin(request.user) and role_name in _PRIVILEGED_ROLES:
            return Response(
                {"detail": f"Only super_admin can remove: {_PRIVILEGED_ROLES}"},
                status=status.HTTP_403_FORBIDDEN,
            )

        user = self._get_user_or_404(pk)
        current = list(user.roles or ["user"])
        new_roles = [r for r in current if r != role_name]
        if not new_roles:
            new_roles = ["user"]
        self._guard_last_super_admin(user, new_roles)
        UserBackend = _get_user_backend()
        UserBackend.update_roles(pk, new_roles)
        return Response({"id": str(user.id), "roles": new_roles})

    # ------------------------------------------------------------------ #
    # POST /api/users/<id>/set-password/
    # ------------------------------------------------------------------ #
    @swagger_auto_schema(
        tags=_TAG,
        operation_summary="Set or reset a user's password (super_admin only)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["password"],
            properties={
                "password": openapi.Schema(type=openapi.TYPE_STRING, description="New password (min 12 chars)"),
            },
        ),
    )
    @action(detail=True, methods=["post"], url_path="set-password")
    def set_password(self, request, pk=None):
        if not _is_super_admin(request.user):
            return Response(
                {"detail": "Only super_admin can set passwords."},
                status=status.HTTP_403_FORBIDDEN,
            )

        password = request.data.get("password") or ""
        if len(password) < 12:
            raise ValidationError({"password": "Password must be at least 12 characters."})

        user = self._get_user_or_404(pk)

        from core.utils.supabase_client import get_supabase_client
        get_supabase_client().table("users").update(
            {"password": make_password(password)}
        ).eq("id", str(user.id)).execute()

        logger.info(f"Password set for user {user.email} by {getattr(request.user, 'email', '?')}")
        return Response({"message": f"Password updated for {user.email}."})

    # ------------------------------------------------------------------ #
    # GET /api/users/me/
    # ------------------------------------------------------------------ #
    @swagger_auto_schema(tags=_TAG, operation_summary="Get current user profile")
    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        return Response(_serialize_user(request.user))

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _get_user_or_404(self, pk: str):
        user = _get_user_backend().get_by_id(pk)
        if not user:
            raise NotFound(f"User '{pk}' not found.")
        return user

    def _is_admin_or_self(self, request, user) -> bool:
        if _is_tenant_admin(request.user):
            return True
        return str(getattr(request.user, "id", "")) == str(user.id)

    def _guard_last_super_admin(self, target_user, new_roles):
        """Prevent removing super_admin from the only remaining super admin."""
        if "super_admin" not in (target_user.roles or []):
            return
        if "super_admin" in new_roles:
            return
        UserBackend = _get_user_backend()
        all_users, _ = UserBackend.list_all(page=1, page_size=1000)
        sa_count = sum(1 for u in all_users if "super_admin" in (u.roles or []))
        if sa_count <= 1:
            raise ValidationError("Cannot remove super_admin from the last super admin user.")
