"""
Notification inbox API — any authenticated user.

GET  /api/notifications/              List notifications for the current user
GET  /api/notifications/unread-count/ Unread badge count
POST /api/notifications/read-all/     Mark all as read
GET  /api/notifications/<id>/         Get single notification
PATCH /api/notifications/<id>/read/   Mark single as read
DELETE /api/notifications/<id>/       Delete a notification
"""
import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authentication import CustomJWTAuthentication
from core.utils.supabase_notifications import SupabaseNotification

logger = logging.getLogger(__name__)


def _resolve_tenant_id(request) -> str | None:
    user = getattr(request, "user", None)
    roles = getattr(user, "roles", None) or []
    if "super_admin" in roles:
        override = request.query_params.get("tenant_id")
        if override:
            return str(override)
    return getattr(request, "_tenant_id", None) or getattr(user, "tenant_id", None)


def _resolve_user_id(request) -> str | None:
    user = getattr(request, "user", None)
    return str(user.id) if user and getattr(user, "id", None) else None


class NotificationListView(APIView):
    """
    GET  /api/notifications/  — list notifications for the current user
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tenant_id = _resolve_tenant_id(request)
        if not tenant_id:
            return Response({"error": "Tenant not resolved"}, status=status.HTTP_400_BAD_REQUEST)

        user_id   = _resolve_user_id(request)
        page      = max(1, int(request.query_params.get("page", 1)))
        page_size = min(100, max(1, int(request.query_params.get("page_size", 20))))

        # Optional filters
        is_read_param = request.query_params.get("is_read")
        is_read = None
        if is_read_param is not None:
            is_read = is_read_param.lower() == "true"

        severity   = request.query_params.get("severity") or None
        event_type = request.query_params.get("event_type") or None

        notifications, total = SupabaseNotification.list_for_user(
            tenant_id=tenant_id,
            user_id=user_id,
            is_read=is_read,
            severity=severity,
            event_type=event_type,
            page=page,
            page_size=page_size,
        )
        return Response({
            "total":     total,
            "page":      page,
            "page_size": page_size,
            "results":   [n.to_dict() for n in notifications],
        }, status=status.HTTP_200_OK)


class NotificationUnreadCountView(APIView):
    """
    GET /api/notifications/unread-count/  — returns {"count": N} for the badge
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tenant_id = _resolve_tenant_id(request)
        if not tenant_id:
            return Response({"error": "Tenant not resolved"}, status=status.HTTP_400_BAD_REQUEST)

        user_id = _resolve_user_id(request)
        count   = SupabaseNotification.unread_count(tenant_id=tenant_id, user_id=user_id)
        return Response({"count": count}, status=status.HTTP_200_OK)


class NotificationReadAllView(APIView):
    """
    POST /api/notifications/read-all/  — mark all unread as read
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        tenant_id = _resolve_tenant_id(request)
        if not tenant_id:
            return Response({"error": "Tenant not resolved"}, status=status.HTTP_400_BAD_REQUEST)

        user_id = _resolve_user_id(request)
        updated = SupabaseNotification.mark_all_read(tenant_id=tenant_id, user_id=user_id)
        return Response({"marked_read": updated}, status=status.HTTP_200_OK)


class NotificationDetailView(APIView):
    """
    GET    /api/notifications/<id>/       Get single notification
    PATCH  /api/notifications/<id>/read/  Mark as read  (handled by NotificationMarkReadView)
    DELETE /api/notifications/<id>/       Delete notification
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, notification_id):
        tenant_id = _resolve_tenant_id(request)
        if not tenant_id:
            return Response({"error": "Tenant not resolved"}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch and return a single notification (tenant-scoped for safety)
        notifications, _ = SupabaseNotification.list_for_user(
            tenant_id=tenant_id,
            user_id=_resolve_user_id(request),
            page=1, page_size=200,
        )
        match = next((n for n in notifications if str(n.id) == str(notification_id)), None)
        if not match:
            return Response({"error": "Notification not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(match.to_dict(), status=status.HTTP_200_OK)

    def delete(self, request, notification_id):
        tenant_id = _resolve_tenant_id(request)
        if not tenant_id:
            return Response({"error": "Tenant not resolved"}, status=status.HTTP_400_BAD_REQUEST)

        deleted = SupabaseNotification.delete(notification_id, tenant_id)
        if not deleted:
            return Response({"error": "Notification not found or already deleted"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"message": "Notification deleted"}, status=status.HTTP_200_OK)


class NotificationMarkReadView(APIView):
    """
    PATCH /api/notifications/<id>/read/  — mark a single notification as read
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, notification_id):
        tenant_id = _resolve_tenant_id(request)
        if not tenant_id:
            return Response({"error": "Tenant not resolved"}, status=status.HTTP_400_BAD_REQUEST)

        updated = SupabaseNotification.mark_read(notification_id, tenant_id)
        if not updated:
            return Response({"error": "Notification not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"message": "Marked as read"}, status=status.HTTP_200_OK)
