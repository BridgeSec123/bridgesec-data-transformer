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
        "okta_app_id":          getattr(tenant, "okta_app_id", None),
        "is_active":            tenant.is_active,
        "created_at":           tenant.created_at if isinstance(tenant.created_at, str) else (
            tenant.created_at.isoformat() if tenant.created_at else None
        ),
        # Sensitive fields omitted from response: okta_client_secret, mongo_uri, private key
    }


def _save_app_user_to_mongo(tenant, okta_user_id, email):
    """
    Write the newly assigned app_user to the MongoDB snapshot.
    No-op for now — uncomment body when real-time UI visibility is needed.
    """
    # TODO: enable when ready
    # from core.utils.tenant_utils import get_mongo_client_for_tenant
    # mongo_client = get_mongo_client_for_tenant(tenant)
    # all_dbs = mongo_client.list_database_names()
    # prefix = (tenant.mongo_db_prefix or "").rstrip("_")
    # matching = sorted([db for db in all_dbs if db.startswith(prefix + "_")])
    # if matching:
    #     mongo_client[matching[-1]]["okta_app_user"].update_one(
    #         {"user_id": okta_user_id, "app_id": tenant.okta_app_id},
    #         {"$set": {"user_id": okta_user_id, "app_id": tenant.okta_app_id, "username": email}},
    #         upsert=True,
    #     )
    pass


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

            # Auto-map the creating super admin into user_tenants for this tenant.
            # This ensures the super admin appears in the tenant switcher immediately
            # and the login flow can resolve them to this tenant.
            try:
                from core.utils.supabase_user_tenant import SupabaseUserTenant
                admin_user = request.user
                SupabaseUserTenant.add(
                    str(admin_user.id), str(tenant.id), role="super_admin"
                )
                logger.info(
                    f"Super admin '{getattr(admin_user, 'email', admin_user.id)}' "
                    f"auto-mapped to new tenant '{tenant.name}'"
                )
            except Exception as map_err:
                logger.warning(f"Could not auto-map super admin to tenant '{tenant.name}': {map_err}")

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
            "okta_app_id",
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

        okta_user_id = request.data.get("okta_user_id")
        email        = (request.data.get("email") or "").strip().lower()
        first_name   = request.data.get("first_name", "")
        last_name    = request.data.get("last_name", "")
        role         = request.data.get("role", "user")

        if not okta_user_id or not email:
            return Response(
                {"error": "okta_user_id and email are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from core.utils.supabase_tenant import SupabaseTenant
        from core.utils.supabase_user import SupabaseUser
        from core.utils.supabase_user_tenant import SupabaseUserTenant
        from core.utils.okta_helpers import build_okta_url, make_okta_request

        # 1. Load tenant and verify okta_app_id is configured
        tenant = SupabaseTenant.get_by_id(str(tenant_id))
        if not tenant:
            return Response({"error": "Tenant not found"}, status=status.HTTP_404_NOT_FOUND)
        if not tenant.okta_app_id:
            return Response(
                {"error": "Tenant app not configured. Set okta_app_id on this tenant first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 2. Get or create Supabase user
        user = SupabaseUser.get_by_email(email)
        if not user:
            username = f"{first_name} {last_name}".strip() or email
            user = SupabaseUser.create_or_update(
                email=email,
                username=username,
                roles=[role],
                tenant_id=str(tenant_id),
                okta_user_id=okta_user_id,
            )
        elif not getattr(user, "okta_user_id", None):
            user.okta_user_id = okta_user_id
            user.save()

        # 3. Add to user_tenants junction table
        row = SupabaseUserTenant.add(str(user.id), str(tenant_id), role=role)
        if row is None:
            return Response(
                {"error": "Failed to add user to tenant"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 4. Update users.tenant_id so JWT carries this tenant on login
        user.tenant_id = str(tenant_id)
        user.save()

        # 5. Assign user to Okta app using current session token
        domain = (tenant.okta_domain or "").rstrip("/")
        if not domain.startswith("http"):
            domain = f"https://{domain}"
        okta_url = build_okta_url(
            f"/api/v1/apps/{tenant.okta_app_id}/users",
            okta_base=domain,
        )
        _, err = make_okta_request(okta_url, request=request, method="POST", data={"id": okta_user_id})
        if err:
            if err.get("status_code") != 409:  # 409 = already assigned, treat as success
                logger.error(f"Okta app user assignment failed: {err}")
                return Response(
                    {"error": f"Okta assignment failed: {err.get('message', err)}"},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

        _save_app_user_to_mongo(tenant, okta_user_id, email)

        logger.info(
            f"User '{email}' (okta_id={okta_user_id}) assigned to tenant '{tenant_id}' "
            f"with role '{role}' by {getattr(request.user, 'email', 'unknown')}"
        )
        return Response(
            {
                "id":           str(user.id),
                "email":        user.email,
                "okta_user_id": okta_user_id,
                "tenant_id":    str(tenant_id),
                "role":         role,
            },
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
        from core.utils.supabase_user_tenant import SupabaseUserTenant
        from core.utils.supabase_tenant import SupabaseTenant
        from core.utils.okta_helpers import build_okta_url, make_okta_request

        user = SupabaseUser.get_by_id(str(uid))
        if not user:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        tenant = SupabaseTenant.get_by_id(str(tenant_id))
        okta_user_id = getattr(user, "okta_user_id", None)

        # Remove from Okta app if both IDs are available
        if tenant and tenant.okta_app_id and okta_user_id:
            domain = (tenant.okta_domain or "").rstrip("/")
            if not domain.startswith("http"):
                domain = f"https://{domain}"
            okta_url = build_okta_url(
                f"/api/v1/apps/{tenant.okta_app_id}/users/{okta_user_id}",
                okta_base=domain,
            )
            _, err = make_okta_request(okta_url, request=request, method="DELETE")
            if err and err.get("status_code") != 404:  # 404 = already removed, continue
                logger.error(f"Okta app user removal failed: {err}")
                return Response(
                    {"error": f"Okta removal failed: {err.get('message', err)}"},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

        # Remove from user_tenants junction table
        SupabaseUserTenant.remove(str(uid), str(tenant_id))

        # Clear users.tenant_id if it was pointing to this tenant
        if str(getattr(user, "tenant_id", None)) == str(tenant_id):
            user.tenant_id = None
            user.save()

        logger.info(
            f"User '{user.email}' removed from tenant '{tenant_id}' "
            f"by {getattr(request.user, 'email', 'unknown')}"
        )
        return Response({"message": "User removed from tenant"}, status=status.HTTP_200_OK)
