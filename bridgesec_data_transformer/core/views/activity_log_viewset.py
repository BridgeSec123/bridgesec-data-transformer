"""
Activity log API — returns per-tenant audit entries from Supabase.

GET /logs/
    ?action=      filter by action type (login, bulk_fetch, restore, create, delete, view)
    ?user_email=  filter by user
    ?date_from=   ISO 8601 date string (inclusive)
    ?date_to=     ISO 8601 date string (inclusive)
    ?page=        page number (default 1)
    ?page_size=   entries per page (default 50)
"""
import logging

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authentication import CustomJWTAuthentication

logger = logging.getLogger(__name__)


class ActivityLogViewSet(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

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
            from core.utils.supabase_activity_log import SupabaseActivityLog
            entries, total = SupabaseActivityLog.list_for_tenant(
                tenant_id=str(tenant.id),
                action=request.query_params.get("action"),
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
