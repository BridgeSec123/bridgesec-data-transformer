"""
Tenant management API — super-admin only.

Super-admin = User with 'super_admin' in roles AND tenant_id is None.
Tenant data is stored in Supabase (not MongoDB).

POST   /api/tenants/                    Onboard new tenant
GET    /api/tenants/                    List all tenants
GET    /api/tenants/<id>/               Get tenant details
PUT    /api/tenants/<id>/               Update tenant config
DELETE /api/tenants/<id>/               Deactivate tenant (soft delete)
GET    /api/tenants/<id>/users/         List users in tenant
POST   /api/tenants/<id>/users/         Assign existing user to tenant
DELETE /api/tenants/<id>/users/<uid>/   Remove user from tenant
"""
import logging

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authentication import CustomJWTAuthentication

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = [
    "name", "okta_domain", "okta_client_id", "okta_client_secret",
    "okta_issuer", "mongo_uri", "mongo_db_prefix",
    "terraform_server_url", "terraform_state_path",
]

# Optional: per-tenant Supabase credentials for full data isolation.
# When omitted the master Supabase instance (from .env) is used automatically.
OPTIONAL_FIELDS = ["supabase_url", "supabase_key"]


def _is_super_admin(request) -> bool:
    """Return True if the requesting user holds the super_admin role."""
    user = getattr(request, "user", None)
    if not user:
        return False
    return "super_admin" in (getattr(user, "roles", None) or [])


def _tenant_to_dict(tenant) -> dict:
    return {
        "id":                   str(tenant.id),
        "name":                 tenant.name,
        "okta_domain":          tenant.okta_domain,
        "okta_client_id":       tenant.okta_client_id,
        "okta_issuer":          tenant.okta_issuer,
        "mongo_db_prefix":      tenant.mongo_db_prefix,
        "terraform_server_url": tenant.terraform_server_url,
        "terraform_state_path": tenant.terraform_state_path,
        # supabase_url shown so UI can confirm it's set; supabase_key is write-only
        "supabase_url":         getattr(tenant, "supabase_url", None),
        "has_supabase_key":     bool(getattr(tenant, "supabase_key", None)),
        "is_active":            tenant.is_active,
        "created_at":           tenant.created_at if isinstance(tenant.created_at, str) else (
            tenant.created_at.isoformat() if tenant.created_at else None
        ),
        # Sensitive fields omitted from response: okta_client_secret, mongo_uri, private key
    }


def _check_multi_tenancy():
    if not getattr(settings, "MULTI_TENANCY_ENABLED", False):
        return Response(
            {"error": "Multi-tenancy is not enabled"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return None


class TenantListCreateView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        err = _check_multi_tenancy()
        if err:
            return err
        if not _is_super_admin(request):
            return Response({"error": "Super-admin access required"}, status=status.HTTP_403_FORBIDDEN)

        try:
            from core.utils.supabase_tenant import SupabaseTenant
            page      = max(1, int(request.query_params.get("page", 1)))
            page_size = min(100, max(1, int(request.query_params.get("page_size", 50))))
            active_only = request.query_params.get("active_only", "true").lower() != "false"
            tenants, total = SupabaseTenant.list_all(active_only=active_only, page=page, page_size=page_size)
            return Response({
                "total": total,
                "page": page,
                "page_size": page_size,
                "data": [_tenant_to_dict(t) for t in tenants],
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"TenantListCreateView.get failed: {e}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        err = _check_multi_tenancy()
        if err:
            return err
        if not _is_super_admin(request):
            return Response({"error": "Super-admin access required"}, status=status.HTTP_403_FORBIDDEN)

        body = request.data
        missing = [f for f in REQUIRED_FIELDS if not body.get(f)]
        if missing:
            return Response(
                {"error": f"Missing required fields: {missing}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from core.utils.supabase_tenant import SupabaseTenant
            data = {
                "name":                 body["name"],
                "okta_domain":          body["okta_domain"],
                "okta_client_id":       body["okta_client_id"],
                "okta_client_secret":   body["okta_client_secret"],
                "okta_issuer":          body["okta_issuer"],
                "mongo_uri":            body["mongo_uri"],
                "mongo_db_prefix":      body["mongo_db_prefix"],
                "terraform_server_url": body["terraform_server_url"],
                "terraform_state_path": body["terraform_state_path"],
                "service_client_id":    body.get("service_client_id"),
                "service_private_key":  body.get("service_private_key"),
                "service_scopes":       body.get("service_scopes"),
                # Optional per-tenant Supabase — only included when provided
                "supabase_url":         body.get("supabase_url") or None,
                "supabase_key":         body.get("supabase_key") or None,
            }
            tenant = SupabaseTenant.create(data)
            logger.info(f"New tenant created: '{tenant.name}' by {getattr(request.user, 'email', 'unknown')}")
            return Response(_tenant_to_dict(tenant), status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"TenantListCreateView.post failed: {e}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TenantDetailView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def _get_tenant(self, tenant_id):
        from core.utils.supabase_tenant import SupabaseTenant
        return SupabaseTenant.get_by_id(str(tenant_id))

    def get(self, request, tenant_id):
        err = _check_multi_tenancy()
        if err:
            return err
        if not _is_super_admin(request):
            return Response({"error": "Super-admin access required"}, status=status.HTTP_403_FORBIDDEN)

        tenant = self._get_tenant(tenant_id)
        if not tenant:
            return Response({"error": "Tenant not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(_tenant_to_dict(tenant), status=status.HTTP_200_OK)

    def put(self, request, tenant_id):
        err = _check_multi_tenancy()
        if err:
            return err
        if not _is_super_admin(request):
            return Response({"error": "Super-admin access required"}, status=status.HTTP_403_FORBIDDEN)

        if not self._get_tenant(tenant_id):
            return Response({"error": "Tenant not found"}, status=status.HTTP_404_NOT_FOUND)

        updatable = [
            "name", "okta_client_id", "okta_client_secret", "okta_issuer",
            "mongo_uri", "mongo_db_prefix", "terraform_server_url",
            "terraform_state_path", "service_client_id", "service_private_key",
            "service_scopes", "supabase_url", "supabase_key", "is_active",
        ]
        update_data = {f: request.data[f] for f in updatable if f in request.data}
        if not update_data:
            return Response({"error": "No updatable fields provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from core.utils.supabase_tenant import SupabaseTenant
            tenant = SupabaseTenant.update(str(tenant_id), update_data)
            logger.info(f"Tenant '{tenant_id}' updated by {getattr(request.user, 'email', 'unknown')}")
            return Response(_tenant_to_dict(tenant), status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"TenantDetailView.put failed: {e}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, tenant_id):
        err = _check_multi_tenancy()
        if err:
            return err
        if not _is_super_admin(request):
            return Response({"error": "Super-admin access required"}, status=status.HTTP_403_FORBIDDEN)

        if not self._get_tenant(tenant_id):
            return Response({"error": "Tenant not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            from core.utils.supabase_tenant import SupabaseTenant
            SupabaseTenant.soft_delete(str(tenant_id))
            logger.info(f"Tenant '{tenant_id}' deactivated by {getattr(request.user, 'email', 'unknown')}")
            return Response({"message": "Tenant deactivated"}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"TenantDetailView.delete failed: {e}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TenantUserListView(APIView):
    """GET /api/tenants/<id>/users/  — list users in tenant (super-admin only)
       POST /api/tenants/<id>/users/ — assign existing user to tenant"""

    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, tenant_id):
        if not _is_super_admin(request):
            return Response({"error": "Super-admin access required"}, status=status.HTTP_403_FORBIDDEN)

        from core.utils.supabase_user import SupabaseUser
        page      = max(1, int(request.query_params.get("page", 1)))
        page_size = min(100, max(1, int(request.query_params.get("page_size", 20))))
        users, total = SupabaseUser.list_all(page=page, page_size=page_size, tenant_id=str(tenant_id))
        return Response({
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": [
                {"id": str(u.id), "email": u.email, "username": u.username, "roles": u.roles}
                for u in users
            ],
        })

    def post(self, request, tenant_id):
        if not _is_super_admin(request):
            return Response({"error": "Super-admin access required"}, status=status.HTTP_403_FORBIDDEN)

        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        from core.utils.supabase_user import SupabaseUser
        user = SupabaseUser.get_by_id(str(user_id))
        if not user:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        user.tenant_id = str(tenant_id)
        user.save()
        return Response(
            {"id": str(user.id), "email": user.email, "tenant_id": user.tenant_id},
            status=status.HTTP_200_OK,
        )


class TenantUserDetailView(APIView):
    """DELETE /api/tenants/<id>/users/<uid>/ — remove user from tenant."""

    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, tenant_id, uid):
        if not _is_super_admin(request):
            return Response({"error": "Super-admin access required"}, status=status.HTTP_403_FORBIDDEN)

        from core.utils.supabase_user import SupabaseUser
        user = SupabaseUser.get_by_id(str(uid))
        if not user:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        if str(user.tenant_id) != str(tenant_id):
            return Response({"error": "User does not belong to this tenant"}, status=status.HTTP_400_BAD_REQUEST)

        user.tenant_id = None
        user.save()
        return Response({"message": "User removed from tenant"}, status=status.HTTP_200_OK)
