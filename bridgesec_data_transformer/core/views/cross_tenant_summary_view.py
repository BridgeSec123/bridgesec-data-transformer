"""
Cross-tenant summary API — super-admin only.

GET /api/cross-tenant/summary/

Returns per-tenant: total snapshots, last snapshot, today's snapshot, total users.
Iterates all active tenants from Supabase and reads each tenant's MongoDB directly.
"""
import logging
from datetime import datetime

from django.conf import settings
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authentication import CustomJWTAuthentication

logger = logging.getLogger(__name__)


def _is_super_admin(request) -> bool:
    user = getattr(request, "user", None)
    if not user:
        return False
    return "super_admin" in (getattr(user, "roles", None) or [])


def _build_tenant_summary(tenant, today_display: str) -> dict:
    """
    Connect to a single tenant's MongoDB and extract snapshot/user metrics.
    Errors are caught per-tenant so one bad tenant does not abort the whole response.
    """
    from core.utils.tenant_utils import get_mongo_client_for_tenant
    from core.utils.db_utils import get_db_map

    summary = {
        "id": str(tenant.id),
        "name": tenant.name,
        "total_snapshots": 0,
        "last_snapshot": None,
        "today_snapshot": None,
        "total_users": 0,
    }

    if not tenant.mongo_uri:
        logger.warning(f"cross_tenant_summary: tenant '{tenant.name}' has no mongo_uri — skipping")
        return summary

    try:
        client = get_mongo_client_for_tenant(tenant)
        db_map = get_db_map(client, prefix=tenant.mongo_db_prefix)
        dates = db_map.get("dates", [])

        # dates list is in chronological order because get_db_map iterates
        # sorted(list_database_names()) and DB names are YYYY-MM-DDTHHMM
        summary["total_snapshots"] = sum(d["snapshot_count"] for d in dates)

        if dates:
            last_date_entry = dates[-1]
            last_snap = last_date_entry["snapshots"][-1]
            summary["last_snapshot"] = {
                "db_name": last_snap["db_name"],
                "date": last_date_entry["date"],
                "time": last_snap["time"],
            }

        today_entries = [d for d in dates if d["date"] == today_display]
        if today_entries:
            today_snap = today_entries[0]["snapshots"][-1]
            summary["today_snapshot"] = {
                "db_name": today_snap["db_name"],
                "date": today_entries[0]["date"],
                "time": today_snap["time"],
            }

        latest_db = summary["last_snapshot"]["db_name"] if summary["last_snapshot"] else None
        if latest_db:
            summary["total_users"] = client[latest_db]["okta_user"].count_documents({})

    except Exception as e:
        logger.warning(f"cross_tenant_summary: failed for tenant '{tenant.name}': {e}")

    return summary


class CrossTenantSummaryView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description=(
            "**Super-admin only.**\n\n"
            "Returns a summary for every active tenant:\n"
            "- `total_snapshots` — total MongoDB snapshot databases ever created for this tenant\n"
            "- `last_snapshot` — most recent snapshot (db_name, date DD-MM-YYYY, time HH:MM)\n"
            "- `today_snapshot` — today's snapshot if a fetch ran today, else null\n"
            "- `total_users` — `okta_user` document count in the latest snapshot DB\n\n"
            "Reads existing MongoDB snapshots only — does not trigger any fetch."
        ),
        responses={
            200: openapi.Response(
                description="Per-tenant summary",
                examples={
                    "application/json": {
                        "total_tenants": 2,
                        "generated_at": "2026-06-03T10:00:00Z",
                        "tenants": [
                            {
                                "id": "uuid-t1",
                                "name": "Acme Corp",
                                "total_snapshots": 15,
                                "last_snapshot": {
                                    "db_name": "acme_2026-06-03T0000",
                                    "date": "03-06-2026",
                                    "time": "00:00",
                                },
                                "today_snapshot": {
                                    "db_name": "acme_2026-06-03T0000",
                                    "date": "03-06-2026",
                                    "time": "00:00",
                                },
                                "total_users": 150,
                            },
                            {
                                "id": "uuid-t2",
                                "name": "Beta Inc",
                                "total_snapshots": 0,
                                "last_snapshot": None,
                                "today_snapshot": None,
                                "total_users": 0,
                            },
                        ],
                    }
                },
            ),
            403: openapi.Response(description="Super-admin access required"),
            400: openapi.Response(description="Multi-tenancy is not enabled"),
        },
    )
    def get(self, request):
        if not _is_super_admin(request):
            return Response(
                {"error": "Super-admin access required"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not getattr(settings, "MULTI_TENANCY_ENABLED", False):
            return Response(
                {"error": "Multi-tenancy is not enabled"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from core.utils.supabase_user_tenant import SupabaseUserTenant
        from core.utils.supabase_tenant import SupabaseTenant

        user_id = str(request.user.id)
        # get_tenants_for_user returns partial objects (no mongo_uri/mongo_db_prefix)
        # so fetch full tenant rows individually
        mapped = SupabaseUserTenant.get_tenants_for_user(user_id)
        tenants = [
            t for t in (SupabaseTenant.get_by_id(str(m.id)) for m in mapped)
            if t and t.is_active
        ]
        today_display = datetime.utcnow().strftime("%d-%m-%Y")

        result = [_build_tenant_summary(t, today_display) for t in tenants]

        return Response(
            {
                "total_tenants": len(result),
                "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "tenants": result,
            },
            status=status.HTTP_200_OK,
        )
