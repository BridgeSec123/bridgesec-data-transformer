"""
POST /api/test-okta-push/

Test harness for the okta-push flow.

Flow:
  1. Caller sends { "tenant_id": "<uuid>", "config": { ...okta-push payload... } }
  2. This view fetches the tenant row from Supabase (PEM key lives there)
  3. Obtains an Okta service token for that tenant (auto-detects DPoP)
  4. Runs the same validation + sync logic as okta-push — directly, not via HTTP
  5. Returns the result in the same shape as okta-push

Why direct call instead of HTTP:
  Internal HTTP to SERVER_URL is fragile in Docker / dev setups where
  the server address seen from inside the process differs from outside.
  Calling the sync functions directly is simpler and has no network dependency.
"""
import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authentication import CustomJWTAuthentication
from core.permissions.decorators import require_permission
from core.utils.okta_push_validators import validate_push_payload
from core.utils.supabase_activity_log import SupabaseActivityLog
from core.utils.supabase_tenant import SupabaseTenant
from core.views.okta_push_viewset import (
    _get_service_token,
    _okta_base,
    _sync_app_config,
    _summarize,
)

logger = logging.getLogger(__name__)


class TestOktaPushView(APIView):
    """
    Trigger the okta-push sync for a specific tenant using that tenant's
    service credentials stored in Supabase. Calls sync logic directly —
    no internal HTTP round-trip.
    """
    authentication_classes = [CustomJWTAuthentication]

    @require_permission("test_okta_push")
    def post(self, request):
        data = request.data
        if not isinstance(data, dict):
            return Response(
                {"error": "Request body must be a JSON object"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── 1. Validate required fields ───────────────────────────────────
        tenant_id = (data.get("tenant_id") or "").strip()
        config    = data.get("config")
        logger.warning(
            f"[debug] config type={type(config).__name__} | "
            f"config keys={list(config.keys()) if isinstance(config, dict) else repr(config)[:200]}"
        )

        errors = []
        if not tenant_id:
            errors.append("tenant_id is required")
        if not config or not isinstance(config, dict):
            errors.append("config must be a non-empty JSON object (okta-push payload)")
        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        # ── 2. Validate the config payload ────────────────────────────────
        validation_errors = validate_push_payload(config)
        if validation_errors:
            return Response({"errors": validation_errors}, status=status.HTTP_400_BAD_REQUEST)

        # ── 3. Fetch tenant from Supabase ─────────────────────────────────
        tenant = SupabaseTenant.get_by_id(tenant_id)
        if not tenant:
            return Response(
                {"error": f"Tenant '{tenant_id}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        missing = [
            f for f in ("service_client_id", "service_private_key", "service_scopes")
            if not getattr(tenant, f, None)
        ]
        if missing:
            return Response(
                {
                    "error": "Tenant is missing service credentials",
                    "missing_fields": missing,
                    "hint": "Set these fields on the tenant row in Supabase before calling this endpoint.",
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        # ── 4. Obtain Okta service token (auto-detects DPoP) ──────────────
        # dpop_key is the EC key bound to the token; must be reused for all API calls.
        try:
            service_token, use_dpop, dpop_key = _get_service_token(tenant)
        except ValueError as exc:
            logger.error(
                f"test-okta-push: failed to get service token "
                f"for tenant {tenant_id}: {exc}"
            )
            return Response(
                {
                    "error": "Could not obtain Okta service token for this tenant",
                    "detail": str(exc),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # ── 5. Run sync logic directly (no HTTP round-trip) ───────────────
        base_url = _okta_base(tenant)
        apps_payload = config.get("apps")

        if apps_payload is not None:
            return self._handle_bulk(request, tenant, base_url, service_token, use_dpop, dpop_key, apps_payload)
        return self._handle_single(request, tenant, base_url, service_token, use_dpop, dpop_key, config)

    def _handle_single(self, request, tenant, base_url, service_token, use_dpop, dpop_key, config):
        auth_server_id = config.get("auth_server_id")
        app_id         = config.get("app_id")

        all_changes = _sync_app_config(base_url, service_token, use_dpop, config, dpop_key=dpop_key)
        result_errors = [c for c in all_changes if c.get("status") == "error"]
        summary = _summarize(all_changes)

        SupabaseActivityLog.log(
            user_email=getattr(request.user, "email", "unknown"),
            action="okta_push",
            tenant_id=str(tenant.id),
            entity_name="okta_config",
            status="error" if result_errors else "success",
            ip_address=request.META.get("REMOTE_ADDR"),
            details={
                "source": "test_harness",
                "auth_server_id": auth_server_id,
                "app_id": app_id,
                "use_dpop": use_dpop,
                "summary": summary,
                "changes": all_changes,
            },
        )

        http_status = status.HTTP_207_MULTI_STATUS if result_errors else status.HTTP_200_OK
        return Response(
            {
                "tenant_id":      str(tenant.id),
                "tenant_name":    tenant.name,
                "auth_server_id": auth_server_id,
                "app_id":         app_id,
                "use_dpop":       use_dpop,
                "summary": summary,
                "changes":  all_changes,
                "errors":   result_errors,
            },
            status=http_status,
        )

    def _handle_bulk(self, request, tenant, base_url, service_token, use_dpop, dpop_key, apps_payload):
        results = []
        all_changes = []

        for app_config in apps_payload:
            auth_server_id = app_config.get("auth_server_id")
            app_id = app_config.get("app_id")

            changes = _sync_app_config(base_url, service_token, use_dpop, app_config, dpop_key=dpop_key)
            app_errors = [c for c in changes if c.get("status") == "error"]
            summary = _summarize(changes)
            all_changes.extend(changes)

            SupabaseActivityLog.log(
                user_email=getattr(request.user, "email", "unknown"),
                action="okta_push",
                tenant_id=str(tenant.id),
                entity_name="okta_config",
                status="error" if app_errors else "success",
                ip_address=request.META.get("REMOTE_ADDR"),
                details={
                    "source": "test_harness",
                    "auth_server_id": auth_server_id,
                    "app_id": app_id,
                    "use_dpop": use_dpop,
                    "summary": summary,
                    "changes": changes,
                },
            )

            results.append({
                "app_id": app_id,
                "auth_server_id": auth_server_id,
                "summary": summary,
                "changes": changes,
                "errors": app_errors,
            })

        summary = _summarize(all_changes)
        http_status = status.HTTP_207_MULTI_STATUS if summary["errors"] else status.HTTP_200_OK
        return Response(
            {
                "tenant_id":   str(tenant.id),
                "tenant_name": tenant.name,
                "use_dpop":    use_dpop,
                "results":     results,
                "summary":     summary,
            },
            status=http_status,
        )
