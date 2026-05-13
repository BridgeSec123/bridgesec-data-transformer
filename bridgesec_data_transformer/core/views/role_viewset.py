"""
Role management API.

GET    /api/roles/           List roles visible in current context
POST   /api/roles/           Create a custom role
GET    /api/roles/<name>/    Role detail
PUT    /api/roles/<name>/    Update role (blocked on system roles)
DELETE /api/roles/<name>/    Delete role (blocked on system roles)

Access rules (enforced manually — /api/roles/ is in OPA_BYPASS_PATHS):
- super_admin  : full CRUD on all roles
- tenant_admin : create/update/delete tenant-scoped custom roles only
- others       : GET (read) only
"""
import logging

from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authentication import CustomJWTAuthentication

logger = logging.getLogger(__name__)


def _is_super_admin(user) -> bool:
    return "super_admin" in (getattr(user, "roles", None) or [])


def _is_tenant_admin(user) -> bool:
    roles = getattr(user, "roles", None) or []
    return "super_admin" in roles or "tenant_admin" in roles


def _serialize_role(role) -> dict:
    return {
        "id":           role.id,
        "name":         role.name,
        "display_name": role.display_name,
        "description":  role.description,
        "is_system":    role.is_system,
        "tenant_id":    role.tenant_id,
        "created_at":   role.created_at,
        "created_by":   role.created_by,
    }


class RoleListCreateView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from core.utils.supabase_role import SupabaseRole

        # super_admin sees all global roles; others see global + their tenant's
        if _is_super_admin(request.user):
            tenant_id = None
        else:
            tenant_id = str(getattr(request.user, "tenant_id", "") or "")
            tenant_id = tenant_id or None

        roles = SupabaseRole.list_all(tenant_id=tenant_id)
        return Response({"results": [_serialize_role(r) for r in roles]})

    def post(self, request):
        if not _is_tenant_admin(request.user):
            return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)

        name         = (request.data.get("name") or "").strip().lower().replace(" ", "_")
        display_name = (request.data.get("display_name") or "").strip()
        description  = request.data.get("description") or ""

        if not name or not display_name:
            raise ValidationError({"name": "name and display_name are required."})

        # tenant_admin can only create tenant-scoped roles
        if _is_super_admin(request.user):
            tenant_id = request.data.get("tenant_id") or None
        else:
            tenant_id = str(getattr(request.user, "tenant_id", "") or "")
            if not tenant_id:
                return Response(
                    {"error": "tenant_admin must belong to a tenant to create roles"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        from core.utils.supabase_role import SupabaseRole
        role = SupabaseRole.create({
            "name":         name,
            "display_name": display_name,
            "description":  description,
            "is_system":    False,
            "tenant_id":    tenant_id,
            "created_by":   getattr(request.user, "email", None),
        })
        return Response(_serialize_role(role), status=status.HTTP_201_CREATED)


class RoleDetailView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def _get_or_404(self, name: str):
        from core.utils.supabase_role import SupabaseRole
        role = SupabaseRole.get_by_name(name)
        if not role:
            raise NotFound(f"Role '{name}' not found.")
        return role

    def _can_modify(self, request, role) -> bool:
        """super_admin can modify anything; tenant_admin can modify own tenant's custom roles."""
        if _is_super_admin(request.user):
            return True
        if not _is_tenant_admin(request.user):
            return False
        user_tenant = str(getattr(request.user, "tenant_id", "") or "")
        return (not role.is_system) and str(role.tenant_id or "") == user_tenant

    def get(self, request, name):
        return Response(_serialize_role(self._get_or_404(name)))

    def put(self, request, name):
        role = self._get_or_404(name)
        if not self._can_modify(request, role):
            return Response({"error": "Insufficient permissions"}, status=status.HTTP_403_FORBIDDEN)

        allowed = {"display_name", "description"}
        data = {k: v for k, v in request.data.items() if k in allowed}
        if not data:
            raise ValidationError("No updatable fields provided.")

        from core.utils.supabase_role import SupabaseRole
        updated = SupabaseRole.update(name, data)
        return Response(_serialize_role(updated or role))

    def delete(self, request, name):
        role = self._get_or_404(name)
        if not self._can_modify(request, role):
            return Response({"error": "Insufficient permissions"}, status=status.HTTP_403_FORBIDDEN)

        from core.utils.supabase_role import SupabaseRole
        try:
            SupabaseRole.delete(name)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)
