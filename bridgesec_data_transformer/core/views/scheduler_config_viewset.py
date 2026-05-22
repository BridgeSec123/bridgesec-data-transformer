"""
Scheduler configuration API.

GET  /api/scheduler-config/  — return current schedule + service scopes
PUT  /api/scheduler-config/  — update scheduler_enabled / hour / minute / timezone

Single-tenant mode (MULTI_TENANCY_ENABLED=False):
  GET  → values from Django settings (.env); editable=False
  PUT  → 400 — configure via SCHEDULER_HOUR / SCHEDULER_ENABLED in .env

Multi-tenant mode:
  GET/PUT → operate on the tenants table columns added in migration 005.
  Tenant is resolved from request._tenant (set by middleware); super_admin is tenant-scoped.

Permission: read = any authenticated user; write = super_admin or tenant_admin.
This view intentionally bypasses OPA (listed in OPA_BYPASS_PATHS) and uses its
own inline role check — same pattern as EntityConfigListView.
"""
import logging

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.tenant_utils import get_tenant_from_request

logger = logging.getLogger(__name__)

_WRITE_ROLES = {"super_admin", "tenant_admin"}

AVAILABLE_TIMEZONES = [
    "UTC",
    "US/Eastern",
    "US/Central",
    "US/Mountain",
    "US/Pacific",
    "Europe/London",
    "Europe/Berlin",
    "Europe/Paris",
    "Asia/Kolkata",
    "Asia/Singapore",
    "Asia/Tokyo",
    "Australia/Sydney",
]


def _can_write(request) -> bool:
    roles = set(getattr(request.user, "roles", []) or [])
    return bool(roles & _WRITE_ROLES)


def _resolve_scopes(raw: str) -> list:
    return [s.strip() for s in (raw or "").split() if s.strip()]


def _resolve_tenant(request):
    """Return the tenant attached to the request by middleware."""
    return get_tenant_from_request(request)


class SchedulerConfigView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        multi = getattr(settings, "MULTI_TENANCY_ENABLED", False)
        global_scopes = _resolve_scopes(getattr(settings, "OKTA_SERVICE_SCOPES", ""))

        if not multi:
            return Response({
                "mode": "single_tenant",
                "editable": False,
                "scheduler_enabled": getattr(settings, "SCHEDULER_ENABLED", True),
                "scheduler_hour": getattr(settings, "SCHEDULER_HOUR", 0),
                "scheduler_minute": 0,
                "scheduler_timezone": "UTC",
                "service_scopes": global_scopes,
                "available_timezones": AVAILABLE_TIMEZONES,
            })

        tenant = _resolve_tenant(request)
        if not tenant:
            return Response({"detail": "Tenant not found."}, status=status.HTTP_404_NOT_FOUND)

        tenant_scopes = _resolve_scopes(
            getattr(tenant, "service_scopes", None) or getattr(settings, "OKTA_SERVICE_SCOPES", "")
        )

        return Response({
            "mode": "multi_tenant",
            "editable": _can_write(request),
            "scheduler_enabled": tenant.scheduler_enabled,
            "scheduler_hour": tenant.scheduler_hour,
            "scheduler_minute": tenant.scheduler_minute,
            "scheduler_timezone": tenant.scheduler_timezone,
            "service_scopes": tenant_scopes,
            "available_timezones": AVAILABLE_TIMEZONES,
        })

    def put(self, request):
        if not _can_write(request):
            return Response({"detail": "Insufficient permissions."}, status=status.HTTP_403_FORBIDDEN)

        if not getattr(settings, "MULTI_TENANCY_ENABLED", False):
            return Response(
                {"detail": "Configure scheduler via SCHEDULER_HOUR / SCHEDULER_ENABLED in .env (single-tenant mode)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tenant = _resolve_tenant(request)
        if not tenant:
            return Response({"detail": "Tenant not found."}, status=status.HTTP_404_NOT_FOUND)

        allowed_fields = {"scheduler_enabled", "scheduler_hour", "scheduler_minute", "scheduler_timezone"}
        update = {k: v for k, v in request.data.items() if k in allowed_fields}

        if not update:
            return Response({"detail": "No valid fields provided."}, status=status.HTTP_400_BAD_REQUEST)

        if "scheduler_hour" in update:
            h = int(update["scheduler_hour"])
            if not (0 <= h <= 23):
                return Response({"detail": "scheduler_hour must be 0–23."}, status=status.HTTP_400_BAD_REQUEST)
            update["scheduler_hour"] = h

        if "scheduler_minute" in update:
            m = int(update["scheduler_minute"])
            if not (0 <= m <= 59):
                return Response({"detail": "scheduler_minute must be 0–59."}, status=status.HTTP_400_BAD_REQUEST)
            update["scheduler_minute"] = m

        if "scheduler_timezone" in update and update["scheduler_timezone"] not in AVAILABLE_TIMEZONES:
            return Response(
                {"detail": f"Unknown timezone. Choose from: {', '.join(AVAILABLE_TIMEZONES)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from core.utils.supabase_tenant import SupabaseTenant
        SupabaseTenant.update(str(tenant.id), update)
        logger.info(f"Scheduler config updated for tenant {tenant.id}: {update}")

        return Response({**update, "tenant_id": str(tenant.id)}, status=status.HTTP_200_OK)
