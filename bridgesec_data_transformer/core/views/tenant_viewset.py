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
GET    /api/tenants/<id>/logging-config/  Current logging backend + available backends
PUT    /api/tenants/<id>/logging-config/  Switch logging backend
"""
import logging

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authentication import CustomJWTAuthentication
from core.permissions.decorators import require_permission

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = [
    "name", "okta_domain", "okta_client_id", "okta_client_secret",
    "okta_issuer", "mongo_uri", "mongo_db_prefix",
    "terraform_state_path",
]

# Optional: per-tenant Supabase credentials for full data isolation.
# When omitted the master Supabase instance (from .env) is used automatically.
# terraform_server_url is also optional/unused at runtime now — OkTf is one
# shared instance for every tenant (settings.SERVER_URL), not per-tenant config.
# Kept here only so existing rows with a stored value don't reject on update.
OPTIONAL_FIELDS = [
    "supabase_url", "supabase_key", "supabase_bucket_name",
    "scheduler_enabled", "scheduler_hour", "scheduler_minute", "scheduler_timezone",
    "service_app_id", "oidc_app_id", "terraform_server_url",
    "logging_backend",
]

# Elasticsearch/Splunk/Loki are each ONE shared instance (settings.py) — a
# tenant only picks WHICH backend, never its own connection details, so
# there's nothing else to collect from the user beyond this dropdown.
VALID_LOGGING_BACKENDS = {"elasticsearch", "splunk", "loki"}
LOGGING_BACKEND_LABELS = {
    "elasticsearch": "Elasticsearch",
    "splunk": "Splunk",
    "loki": "Loki",
}


def _available_logging_backends():
    return [{"key": key, "label": label} for key, label in LOGGING_BACKEND_LABELS.items()]


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
        "supabase_bucket_name": getattr(tenant, "supabase_bucket_name", None),
        "okta_app_id":          getattr(tenant, "okta_app_id", None),
        "service_app_id":       getattr(tenant, "service_app_id", None),
        "oidc_app_id":          getattr(tenant, "oidc_app_id", None),
        "alert_email":          getattr(tenant, "alert_email", None),
        "scheduler_enabled":    getattr(tenant, "scheduler_enabled", True),
        "scheduler_hour":       getattr(tenant, "scheduler_hour", 0),
        "scheduler_minute":     getattr(tenant, "scheduler_minute", 0),
        "scheduler_timezone":   getattr(tenant, "scheduler_timezone", "UTC"),
        "logging_backend":      getattr(tenant, "logging_backend", "elasticsearch"),
        "last_scheduled_run":   getattr(tenant, "last_scheduled_run", None),
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

    @require_permission("view_tenants")
    def get(self, request):
        err = _check_multi_tenancy()
        if err:
            return err

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

    @require_permission("create_tenant")
    def post(self, request):
        err = _check_multi_tenancy()
        if err:
            return err

        body = request.data
        missing = [f for f in REQUIRED_FIELDS if not body.get(f)]
        if missing:
            return Response(
                {"error": f"Missing required fields: {missing}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        scheduler_hour   = body.get("scheduler_hour")
        scheduler_minute = body.get("scheduler_minute")
        if scheduler_hour is not None and not (0 <= int(scheduler_hour) <= 23):
            return Response({"error": "scheduler_hour must be 0–23"}, status=status.HTTP_400_BAD_REQUEST)
        if scheduler_minute is not None and not (0 <= int(scheduler_minute) <= 59):
            return Response({"error": "scheduler_minute must be 0–59"}, status=status.HTTP_400_BAD_REQUEST)
        if body.get("logging_backend") and body["logging_backend"] not in VALID_LOGGING_BACKENDS:
            return Response(
                {"error": f"logging_backend must be one of {sorted(VALID_LOGGING_BACKENDS)}"},
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
                "terraform_state_path": body["terraform_state_path"],
                # Unused at runtime (OkTf is one shared instance, see settings.SERVER_URL) —
                # only kept for tenants that already have a stored value.
                "terraform_server_url": body.get("terraform_server_url") or None,
                "service_client_id":    body.get("service_client_id"),
                "service_private_key":  body.get("service_private_key"),
                "service_scopes":       body.get("service_scopes"),
                # Optional per-tenant Supabase — only included when provided
                "supabase_url":         body.get("supabase_url") or None,
                "supabase_key":         body.get("supabase_key") or None,
                "supabase_bucket_name": body.get("supabase_bucket_name") or None,
                "alert_email":          body.get("alert_email") or None,
                "service_app_id":       body.get("service_app_id") or None,
                "oidc_app_id":          body.get("oidc_app_id") or None,
                # Scheduler — omit keys when not provided so DB defaults apply
                **({"scheduler_enabled":  body["scheduler_enabled"]} if "scheduler_enabled" in body else {}),
                **({"scheduler_hour":     int(scheduler_hour)}        if scheduler_hour   is not None else {}),
                **({"scheduler_minute":   int(scheduler_minute)}      if scheduler_minute is not None else {}),
                **({"scheduler_timezone": body["scheduler_timezone"]} if "scheduler_timezone" in body else {}),
                **({"logging_backend": body["logging_backend"]} if "logging_backend" in body else {}),
            }
            tenant = SupabaseTenant.create(data)

            # Auto-map the creating super admin into users for this tenant so
            # the tenant switcher and resolve-tenant can find them immediately.
            try:
                from core.utils.supabase_user import SupabaseUser
                admin_user = request.user
                SupabaseUser.create_or_update(
                    email=admin_user.email,
                    username=getattr(admin_user, "username", None) or admin_user.email,
                    roles=getattr(admin_user, "roles", ["super_admin"]),
                    tenant_id=str(tenant.id),
                    okta_user_id=getattr(admin_user, "okta_user_id", None),
                    app_access_enabled=True,
                )
                logger.info(
                    f"Super admin '{getattr(admin_user, 'email', admin_user.id)}' "
                    f"auto-mapped to new tenant '{tenant.name}'"
                )
            except Exception as map_err:
                logger.warning(f"Could not auto-map super admin to tenant '{tenant.name}': {map_err}")

            logger.info(f"New tenant created: '{tenant.name}' by {getattr(request.user, 'email', 'unknown')}")
            try:
                from core.notifications import notify
                from core.notifications import events
                notify(events.TENANT_CREATED, {'tenant_id': str(tenant.id), 'name': tenant.name, 'by': getattr(request.user, 'email', None)}, str(tenant.id))
            except Exception:
                pass
            return Response(_tenant_to_dict(tenant), status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"TenantListCreateView.post failed: {e}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TenantDetailView(APIView):
    authentication_classes = [CustomJWTAuthentication]

    def _get_tenant(self, tenant_id):
        from core.utils.supabase_tenant import SupabaseTenant
        return SupabaseTenant.get_by_id(str(tenant_id))

    @require_permission("view_tenants")
    def get(self, request, tenant_id):
        err = _check_multi_tenancy()
        if err:
            return err

        tenant = self._get_tenant(tenant_id)
        if not tenant:
            return Response({"error": "Tenant not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(_tenant_to_dict(tenant), status=status.HTTP_200_OK)

    @require_permission("update_tenant")
    def put(self, request, tenant_id):
        err = _check_multi_tenancy()
        if err:
            return err

        if not self._get_tenant(tenant_id):
            return Response({"error": "Tenant not found"}, status=status.HTTP_404_NOT_FOUND)

        updatable = [
            "name", "okta_client_id", "okta_client_secret", "okta_issuer",
            "mongo_uri", "mongo_db_prefix", "terraform_server_url",
            "terraform_state_path", "service_client_id", "service_private_key",
            "service_scopes", "supabase_url", "supabase_key", "supabase_bucket_name",
            "is_active", "okta_app_id", "service_app_id", "oidc_app_id", "alert_email",
            "scheduler_enabled", "scheduler_hour", "scheduler_minute", "scheduler_timezone",
            "logging_backend",
        ]
        update_data = {f: request.data[f] for f in updatable if f in request.data}
        if not update_data:
            return Response({"error": "No updatable fields provided"}, status=status.HTTP_400_BAD_REQUEST)

        if "scheduler_hour" in update_data and not (0 <= int(update_data["scheduler_hour"]) <= 23):
            return Response({"error": "scheduler_hour must be 0–23"}, status=status.HTTP_400_BAD_REQUEST)
        if "scheduler_minute" in update_data and not (0 <= int(update_data["scheduler_minute"]) <= 59):
            return Response({"error": "scheduler_minute must be 0–59"}, status=status.HTTP_400_BAD_REQUEST)
        if "logging_backend" in update_data and update_data["logging_backend"] not in VALID_LOGGING_BACKENDS:
            return Response(
                {"error": f"logging_backend must be one of {sorted(VALID_LOGGING_BACKENDS)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        for f in ("scheduler_hour", "scheduler_minute"):
            if f in update_data:
                update_data[f] = int(update_data[f])

        try:
            from core.utils.supabase_tenant import SupabaseTenant
            from core.utils.tenant_logging_config import invalidate_logging_backend_cache
            tenant = SupabaseTenant.update(str(tenant_id), update_data)
            if "logging_backend" in update_data:
                invalidate_logging_backend_cache(str(tenant_id))
            logger.info(f"Tenant '{tenant_id}' updated by {getattr(request.user, 'email', 'unknown')}")
            return Response(_tenant_to_dict(tenant), status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"TenantDetailView.put failed: {e}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @require_permission("delete_tenant")
    def delete(self, request, tenant_id):
        err = _check_multi_tenancy()
        if err:
            return err

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

    @require_permission("view_tenant_users")
    def get(self, request, tenant_id):

        from core.utils.supabase_user import SupabaseUser
        page      = max(1, int(request.query_params.get("page", 1)))
        page_size = min(100, max(1, int(request.query_params.get("page_size", 20))))
        users, total = SupabaseUser.list_all(page=page, page_size=page_size, tenant_id=str(tenant_id))
        return Response({
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": [
                {
                    "id":                 str(u.id),
                    "email":              u.email,
                    "username":           u.username,
                    "roles":              u.roles,
                    "okta_user_id":       u.okta_user_id,
                    "app_access_enabled": u.app_access_enabled,
                    "tenant_id":          u.tenant_id,
                    "created_at":         u._row.get("created_at"),
                }
                for u in users
            ],
        })

    @require_permission("assign_tenant_user")
    def post(self, request, tenant_id):

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

        # 2. Upsert user row for this (email, tenant_id) with app access enabled.
        #    create_or_update uses on_conflict="email,tenant_id" so re-inviting is safe.
        username = f"{first_name} {last_name}".strip() or email
        user = SupabaseUser.create_or_update(
            email=email,
            username=username,
            roles=[role],
            tenant_id=str(tenant_id),
            okta_user_id=okta_user_id,
            app_access_enabled=True,
        )
        if user is None:
            return Response(
                {"error": "Failed to add user to tenant"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

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

    @require_permission("remove_tenant_user")
    def delete(self, request, tenant_id, uid):

        from core.utils.supabase_user import SupabaseUser
        from core.utils.supabase_tenant import SupabaseTenant
        from core.utils.supabase_client import get_supabase_client
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

        # Revoke app access by disabling the users row for this (user, tenant) combo.
        # Row is kept for audit purposes; app_access_enabled=False prevents login.
        get_supabase_client().table("users").update(
            {"app_access_enabled": False}
        ).eq("id", str(uid)).execute()

        logger.info(
            f"User '{user.email}' removed from tenant '{tenant_id}' "
            f"by {getattr(request.user, 'email', 'unknown')}"
        )
        return Response({"message": "User removed from tenant"}, status=status.HTTP_200_OK)


class TenantLoggingConfigView(APIView):
    """
    GET /api/tenants/<id>/logging-config/  — current backend + the list of
        available backends, so the UI can render a dropdown
        (elasticsearch/splunk/loki). Each backend is ONE shared instance
        (settings.py) — there's no per-tenant connection config to collect.
    PUT /api/tenants/<id>/logging-config/  — body: {"logging_backend": "..."}.
    """

    authentication_classes = [CustomJWTAuthentication]

    @require_permission("view_tenant_logging_config")
    def get(self, request, tenant_id):
        err = _check_multi_tenancy()
        if err:
            return err

        from core.utils.supabase_tenant import SupabaseTenant
        tenant = SupabaseTenant.get_by_id(str(tenant_id))
        if not tenant:
            return Response({"error": "Tenant not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "tenant_id": str(tenant_id),
            "logging_backend": tenant.logging_backend,
            "available_backends": _available_logging_backends(),
        }, status=status.HTTP_200_OK)

    @require_permission("update_tenant_logging_config")
    def put(self, request, tenant_id):
        err = _check_multi_tenancy()
        if err:
            return err

        from core.utils.supabase_tenant import SupabaseTenant
        tenant = SupabaseTenant.get_by_id(str(tenant_id))
        if not tenant:
            return Response({"error": "Tenant not found"}, status=status.HTTP_404_NOT_FOUND)

        backend = request.data.get("logging_backend")
        if backend not in VALID_LOGGING_BACKENDS:
            return Response(
                {"error": f"logging_backend must be one of {sorted(VALID_LOGGING_BACKENDS)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from core.utils.tenant_logging_config import invalidate_logging_backend_cache
            SupabaseTenant.update(str(tenant_id), {"logging_backend": backend})
            invalidate_logging_backend_cache(str(tenant_id))
            logger.info(
                f"Logging backend for tenant '{tenant_id}' set to '{backend}' "
                f"by {getattr(request.user, 'email', 'unknown')}"
            )
            return Response({
                "tenant_id": str(tenant_id),
                "logging_backend": backend,
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"TenantLoggingConfigView.put failed: {e}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
