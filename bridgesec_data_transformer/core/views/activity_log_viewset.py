"""
Activity log API — returns per-tenant audit entries from Supabase.

GET /logs/
    ?operations_only=true   shortcut: return only UI operation actions
                            (bulk_fetch, restore, create, delete, compare, migrate)
    ?action=      filter by single action type
    ?actions=     comma-separated action list, e.g. bulk_fetch,restore,delete
    ?user_email=  filter by user
    ?date_from=   ISO 8601 date string (inclusive)
    ?date_to=     ISO 8601 date string (inclusive)
    ?page=        page number (default 1)
    ?page_size=   entries per page (default 50)
"""
import logging

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authentication import CustomJWTAuthentication
from core.permissions.decorators import require_permission

logger = logging.getLogger(__name__)

OPERATION_ACTIONS = ["bulk_fetch", "restore", "create", "delete", "compare", "migrate"]


class ActivityLogViewSet(APIView):
    authentication_classes = [CustomJWTAuthentication]

    @require_permission("view_activity_logs")
    def get(self, request):
        if not getattr(settings, "MULTI_TENANCY_ENABLED", False):
            return Response(
                {"error": "Activity logs are only available in multi-tenant mode"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tenant = getattr(request, "_tenant", None)
        if not tenant:
            return Response(
                {"error": "Tenant context required to view activity logs"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            page = max(1, int(request.query_params.get("page", 1)))
            page_size = min(200, max(1, int(request.query_params.get("page_size", 50))))
        except ValueError:
            return Response(
                {"error": "page and page_size must be integers"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # ?operations_only=true overrides any action/actions param
            if request.query_params.get("operations_only", "").lower() == "true":
                actions_list = OPERATION_ACTIONS
            else:
                raw_actions = request.query_params.get("actions")
                actions_list = [a.strip() for a in raw_actions.split(",") if a.strip()] if raw_actions else None

            from core.utils.supabase_activity_log import SupabaseActivityLog
            entries, total = SupabaseActivityLog.list_for_tenant(
                tenant_id=str(tenant.id),
                action=request.query_params.get("action"),
                actions=actions_list,
                user_email=request.query_params.get("user_email"),
                date_from=request.query_params.get("date_from"),
                date_to=request.query_params.get("date_to"),
                page=page,
                page_size=page_size,
            )
            return Response(
                {
                    "total":     total,
                    "page":      page,
                    "page_size": page_size,
                    "data":      entries,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"ActivityLogViewSet.get failed: {e}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
