import logging

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from core.authentication import CustomJWTAuthentication
from core.serializers.login_serializer import UserLoginSerializer
from core.utils.jwt_utils import generate_jwt_token

logger = logging.getLogger(__name__)

class CustomTokenObtainPairView(TokenObtainPairView):
    entity_type = "auth"
    # @swagger_auto_schema(
    #     operation_description="Obtain a new JWT token by providing valid user credentials",
    #     responses={200: openapi.Response('Token pair obtained')}
    # )
    # def post(self, request, *args, **kwargs):
    #     return super().post(request, *args, **kwargs)
    @swagger_auto_schema(
        request_body=UserLoginSerializer,
        operation_description="Login and get JWT token",
        responses={200: "JWT Token returned"}
    )
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]
            token = generate_jwt_token(user)
            return Response({"token": token}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenRefreshView(TokenRefreshView):
    entity_type = "auth"
    @swagger_auto_schema(
        operation_description="Refresh your JWT token using a valid refresh token",
        responses={200: openapi.Response('Token refreshed')},
        tags=["login"]
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class CustomTokenObtainView(APIView):
    entity_type = "auth"
    @swagger_auto_schema(
        request_body=UserLoginSerializer,
        operation_description="Login and get JWT token",
        responses={200: "JWT Token returned"},
        tags=["login"]
    )
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]

            #  Generate a JWT with user_id, email, role, exp
            token = generate_jwt_token(user)

            # Return token to frontend
            return Response({"token": token}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def _resolve_default_tenant_for_user(user):
    """
    Pick the default login tenant for any user.

    Priority:
    1. user.tenant_id — sticky last-used / seeded home tenant, validated against
       active membership (prevents redirect to a tenant the user was removed from).
    2. First row in user_tenants for this user.
    3. (super_admin only) First active tenant in the system as a last resort.
    """
    from core.utils.supabase_tenant import SupabaseTenant
    from core.utils.supabase_user_tenant import SupabaseUserTenant

    is_super_admin = "super_admin" in (getattr(user, "roles", None) or [])
    assigned = SupabaseUserTenant.get_tenants_for_user(user.id)
    assigned_ids = {str(t.id) for t in assigned}

    if getattr(user, "tenant_id", None):
        candidate_id = str(user.tenant_id)
        # Only use the stored pointer if the user is still an active member.
        if candidate_id in assigned_ids:
            tenant = SupabaseTenant.get_by_id(candidate_id)
            if tenant and tenant.is_active:
                return tenant

    if assigned:
        return assigned[0]

    # Super admin fallback: any active tenant in the system.
    if is_super_admin:
        tenants, _ = SupabaseTenant.list_all(active_only=True)
        return tenants[0] if tenants else None

    return None


class ResolveTenantView(APIView):
    """
    POST /api/auth/resolve-tenant/
    Public endpoint — called before Okta login to determine which tenant to
    direct the user to. Always returns a redirect_url; never returns a picker.

    The default tenant is chosen by _resolve_default_tenant_for_user():
      1. users.tenant_id (sticky last-used, seeded as home tenant), if still member
      2. First row in user_tenants
      3. (super_admin only) First active tenant in the system

    After login the Okta callback updates users.tenant_id so the pointer stays
    sticky to the last tenant used. In-app tenant switching is available via
    GET /api/auth/my-tenants/ + redirect to /okta/login/?okta_domain=…&force_login=false.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username", "").strip()
        if not username:
            return Response({"error": "Username is required"}, status=status.HTTP_400_BAD_REQUEST)

        from core.utils.supabase_user import SupabaseUser
        user = SupabaseUser.get_by_username(username)
        if not user:
            logger.info(f"resolve-tenant: unknown username '{username}'")
            return Response(
                {"error": "Username not found. Contact your administrator."},
                status=status.HTTP_404_NOT_FOUND,
            )

        is_super_admin = "super_admin" in (user.roles or [])
        default_tenant = _resolve_default_tenant_for_user(user)

        if not default_tenant:
            logger.warning(f"resolve-tenant: user '{username}' has no tenants available")
            return Response(
                {"requires_tenant_selection": False, "tenants": []},
                status=status.HTTP_200_OK,
            )

        logger.info(f"resolve-tenant: user '{username}' → default tenant '{default_tenant.name}'")
        login_hint = getattr(user, "email", "") or ""
        redirect_url = f"/okta/login/?okta_domain={default_tenant.okta_domain}&force_login=true"
        if login_hint:
            redirect_url += f"&login_hint={login_hint}"
        return Response({
            "requires_tenant_selection": False,
            "is_super_admin": is_super_admin,
            "redirect_url": redirect_url,
        })


class MyTenantsView(APIView):
    """
    GET /api/auth/my-tenants/
    Returns the authenticated user's tenant memberships with roles.
    Used by the in-app tenant switcher — frontend uses this to render the
    workspace list, then switches by redirecting to:
      /okta/login/?okta_domain=<target_okta_domain>&force_login=false

    Super admins see all active tenants (they can operate on any).
    Regular users see only their assigned tenants.

    Response:
      {
        "current_tenant_id": "<uuid>",
        "tenants": [
          { "id": "…", "name": "…", "okta_domain": "…", "role": "…", "current": true|false }
        ]
      }
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from core.utils.supabase_user_tenant import SupabaseUserTenant
        from core.utils.supabase_tenant import SupabaseTenant

        user = request.user
        current_tenant_id = getattr(request, "_tenant_id", None)
        is_super_admin = "super_admin" in (getattr(user, "roles", None) or [])
        user_email = getattr(user, "email", "") or ""
        login_hint_param = f"&login_hint={user_email}" if user_email else ""

        tenant_entries = []

        if is_super_admin:
            all_tenants, _ = SupabaseTenant.list_all(active_only=True)
            for t in all_tenants:
                tenant_entries.append({
                    "id": str(t.id),
                    "name": t.name,
                    "okta_domain": t.okta_domain,
                    "role": "super_admin",
                    "current": str(t.id) == str(current_tenant_id),
                    "switch_url": f"/okta/login/?okta_domain={t.okta_domain}&force_login=false{login_hint_param}",
                })
        else:
            assigned = SupabaseUserTenant.get_tenants_for_user(str(user.id))
            roles_map = {}
            try:
                from core.utils.supabase_client import get_supabase_client
                result = (
                    get_supabase_client()
                    .table("user_tenants")
                    .select("tenant_id, role")
                    .eq("user_id", str(user.id))
                    .execute()
                )
                roles_map = {row["tenant_id"]: row["role"] for row in (result.data or [])}
            except Exception as e:
                logger.warning(f"my-tenants: role lookup failed for user {user.id}: {e}")

            for t in assigned:
                tenant_entries.append({
                    "id": str(t.id),
                    "name": t.name,
                    "okta_domain": t.okta_domain,
                    "role": roles_map.get(str(t.id), "user"),
                    "current": str(t.id) == str(current_tenant_id),
                    "switch_url": f"/okta/login/?okta_domain={t.okta_domain}&force_login=false{login_hint_param}",
                })

        return Response({
            "current_tenant_id": str(current_tenant_id) if current_tenant_id else None,
            "login_hint": getattr(user, "email", "") or "",
            "tenants": tenant_entries,
        })


class CurrentTenantView(APIView):
    """
    GET /api/auth/me/
    Returns the authenticated user's identity and the tenant resolved from their JWT.
    Use this to verify which tenant is active for every request.
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.conf import settings
        from core.utils.tenant_utils import resolve_tenant_for_request

        user = request.user
        tenant_id_from_jwt = getattr(request, '_tenant_id', None)
        tenant = resolve_tenant_for_request(request)

        mongo_status = "not_checked"
        snapshot_count = 0
        latest_snapshot = None

        if tenant:
            try:
                from core.utils.tenant_utils import get_mongo_client_for_tenant
                client = get_mongo_client_for_tenant(tenant)
                prefix = tenant.mongo_db_prefix or ''
                dbs = [d for d in client.list_database_names()
                       if '_' in d and d.startswith(prefix + '_')]
                snapshot_count = len(dbs)
                latest_snapshot = sorted(dbs)[-1] if dbs else None
                mongo_status = "connected"
            except Exception as e:
                mongo_status = f"error: {str(e)}"

        cluster = None
        if tenant and tenant.mongo_uri:
            try:
                cluster = tenant.mongo_uri.split('@')[-1].split('/')[0]
            except Exception:
                cluster = tenant.mongo_uri[:40]

        return Response({
            "user": {
                "user_id": str(user.id),
                "email":   user.email,
                "roles":   getattr(user, 'roles', []),
            },
            "jwt": {
                "tenant_id": tenant_id_from_jwt,
            },
            "resolved_tenant": {
                "id":              str(tenant.id),
                "name":            tenant.name,
                "okta_domain":     tenant.okta_domain,
                "mongo_db_prefix": tenant.mongo_db_prefix,
                "mongo_cluster":   cluster,
            } if tenant else None,
            "mongodb": {
                "status":          mongo_status,
                "snapshot_count":  snapshot_count,
                "latest_snapshot": latest_snapshot,
            },
            "multi_tenancy_enabled": getattr(settings, 'MULTI_TENANCY_ENABLED', False),
            "warning": (
                None if tenant
                else "No tenant resolved — JWT tenant_id missing or Supabase lookup failed. Using global MongoDB."
            ),
        })
