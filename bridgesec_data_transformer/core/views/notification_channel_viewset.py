"""
Notification channel config API — tenant-admin only.

GET    /api/notification-channels/           List all channels for the tenant
POST   /api/notification-channels/           Create / upsert a channel config
GET    /api/notification-channels/<id>/      Get single channel config
PATCH  /api/notification-channels/<id>/      Update channel config
DELETE /api/notification-channels/<id>/      Remove channel config
POST   /api/notification-channels/<id>/test/ Send a test notification to the channel
"""
import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authentication import CustomJWTAuthentication
from core.permissions.decorators import require_permission
from core.utils.supabase_notifications import SupabaseNotificationChannel, VALID_CHANNEL_TYPES

logger = logging.getLogger(__name__)

UPDATABLE_FIELDS = {"is_enabled", "config", "event_filter"}


def _resolve_tenant_id(request) -> str | None:
    """Return tenant_id from JWT claim or super-admin ?tenant_id= override."""
    user = getattr(request, "user", None)
    roles = getattr(user, "roles", None) or []
    if "super_admin" in roles:
        override = request.query_params.get("tenant_id")
        if override:
            return str(override)
    return getattr(request, "_tenant_id", None) or getattr(user, "tenant_id", None)


class NotificationChannelListView(APIView):
    """
    GET  /api/notification-channels/  — list all channel configs for the tenant
    POST /api/notification-channels/  — upsert a channel config
    """
    authentication_classes = [CustomJWTAuthentication]

    @require_permission("view_notification_channels")
    def get(self, request):
        tenant_id = _resolve_tenant_id(request)
        if not tenant_id:
            return Response({"error": "Tenant not resolved"}, status=status.HTTP_400_BAD_REQUEST)

        channels = SupabaseNotificationChannel.list_for_tenant(tenant_id)
        return Response({"results": [c.to_dict() for c in channels]}, status=status.HTTP_200_OK)

    @require_permission("create_notification_channel")
    def post(self, request):
        tenant_id = _resolve_tenant_id(request)
        if not tenant_id:
            return Response({"error": "Tenant not resolved"}, status=status.HTTP_400_BAD_REQUEST)

        channel_type = request.data.get("channel_type", "").strip().lower()
        if channel_type not in VALID_CHANNEL_TYPES:
            return Response(
                {"error": f"channel_type must be one of: {sorted(VALID_CHANNEL_TYPES)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate webhook_url is present for Slack/Teams
        config = request.data.get("config") or {}
        if channel_type in ("slack", "teams") and not config.get("webhook_url"):
            return Response(
                {"error": f"config.webhook_url is required for {channel_type}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if channel_type == "email" and not config.get("recipients"):
            return Response(
                {"error": "config.recipients is required for email (list of addresses)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = {
            "is_enabled":   request.data.get("is_enabled", True),
            "config":       config,
            "event_filter": request.data.get("event_filter"),  # None = all events
        }

        try:
            channel = SupabaseNotificationChannel.upsert(tenant_id, channel_type, data)
            logger.info(
                f"NotificationChannel '{channel_type}' upserted for tenant {tenant_id} "
                f"by {getattr(request.user, 'email', 'unknown')}"
            )
            return Response(channel.to_dict(), status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"NotificationChannelListView.post failed: {e}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NotificationChannelDetailView(APIView):
    """
    GET    /api/notification-channels/<id>/      Get single channel config
    PATCH  /api/notification-channels/<id>/      Update channel config
    DELETE /api/notification-channels/<id>/      Remove channel config
    """
    authentication_classes = [CustomJWTAuthentication]

    def _get_channel(self, channel_id, tenant_id):
        channel = SupabaseNotificationChannel.get_by_id(channel_id, tenant_id)
        if not channel:
            return None, Response({"error": "Channel not found"}, status=status.HTTP_404_NOT_FOUND)
        return channel, None

    @require_permission("view_notification_channels")
    def get(self, request, channel_id):
        tenant_id = _resolve_tenant_id(request)
        if not tenant_id:
            return Response({"error": "Tenant not resolved"}, status=status.HTTP_400_BAD_REQUEST)

        channel, err = self._get_channel(channel_id, tenant_id)
        if err:
            return err
        return Response(channel.to_dict(), status=status.HTTP_200_OK)

    @require_permission("update_notification_channel")
    def patch(self, request, channel_id):
        tenant_id = _resolve_tenant_id(request)
        if not tenant_id:
            return Response({"error": "Tenant not resolved"}, status=status.HTTP_400_BAD_REQUEST)

        _, err = self._get_channel(channel_id, tenant_id)
        if err:
            return err

        update_data = {k: request.data[k] for k in UPDATABLE_FIELDS if k in request.data}
        if not update_data:
            return Response(
                {"error": f"No updatable fields provided. Allowed: {sorted(UPDATABLE_FIELDS)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            updated = SupabaseNotificationChannel.update(channel_id, tenant_id, update_data)
            if not updated:
                return Response({"error": "Update failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            logger.info(
                f"NotificationChannel {channel_id} updated for tenant {tenant_id} "
                f"by {getattr(request.user, 'email', 'unknown')}"
            )
            return Response(updated.to_dict(), status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"NotificationChannelDetailView.patch failed: {e}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @require_permission("delete_notification_channel")
    def delete(self, request, channel_id):
        tenant_id = _resolve_tenant_id(request)
        if not tenant_id:
            return Response({"error": "Tenant not resolved"}, status=status.HTTP_400_BAD_REQUEST)

        _, err = self._get_channel(channel_id, tenant_id)
        if err:
            return err

        deleted = SupabaseNotificationChannel.delete(channel_id, tenant_id)
        if not deleted:
            return Response({"error": "Delete failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logger.info(
            f"NotificationChannel {channel_id} deleted from tenant {tenant_id} "
            f"by {getattr(request.user, 'email', 'unknown')}"
        )
        return Response({"message": "Channel removed"}, status=status.HTTP_200_OK)


class NotificationChannelTestView(APIView):
    """
    POST /api/notification-channels/<id>/test/
    Sends a test payload to the configured channel to verify the webhook works.
    """
    authentication_classes = [CustomJWTAuthentication]

    @require_permission("test_notification_channel")
    def post(self, request, channel_id):
        tenant_id = _resolve_tenant_id(request)
        if not tenant_id:
            return Response({"error": "Tenant not resolved"}, status=status.HTTP_400_BAD_REQUEST)

        channel = SupabaseNotificationChannel.get_by_id(channel_id, tenant_id)
        if not channel:
            return Response({"error": "Channel not found"}, status=status.HTTP_404_NOT_FOUND)

        if not channel.is_enabled:
            return Response({"error": "Channel is disabled — enable it before testing"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = _send_test_notification(channel, request)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"NotificationChannelTestView.post failed for channel {channel_id}: {e}", exc_info=True)
            return Response({"error": str(e), "delivered": False}, status=status.HTTP_502_BAD_GATEWAY)


def _send_test_notification(channel, request) -> dict:
    """Dispatch a test message to the given channel synchronously."""
    import requests as http_requests

    test_payload = {
        "event_type": "test",
        "severity":   "info",
        "title":      "BridgeSec — test notification",
        "body":       f"This is a test from {getattr(request.user, 'email', 'admin')}. Your channel is configured correctly.",
    }

    channel_type = channel.channel_type

    if channel_type == "dashboard":
        # Dashboard is always working if Supabase is up — just return success
        return {"delivered": True, "channel": "dashboard", "message": "Dashboard channel is active"}

    if channel_type in ("slack", "teams"):
        webhook_url = (channel.config or {}).get("webhook_url")
        if not webhook_url:
            raise ValueError("webhook_url not configured")

        if channel_type == "slack":
            body = {
                "text": f"*{test_payload['title']}*\n{test_payload['body']}"
            }
        else:  # teams
            body = {
                "@type":      "MessageCard",
                "@context":   "http://schema.org/extensions",
                "summary":    test_payload["title"],
                "themeColor": "0076D7",
                "title":      test_payload["title"],
                "text":       test_payload["body"],
            }

        resp = http_requests.post(webhook_url, json=body, timeout=10)
        resp.raise_for_status()
        return {"delivered": True, "channel": channel_type, "status_code": resp.status_code}

    if channel_type == "email":
        from django.core.mail import send_mail
        recipients = (channel.config or {}).get("recipients") or []
        if not recipients:
            raise ValueError("No recipients configured")
        send_mail(
            subject=test_payload["title"],
            message=test_payload["body"],
            from_email=None,   # uses DEFAULT_FROM_EMAIL from settings
            recipient_list=recipients,
        )
        return {"delivered": True, "channel": "email", "recipients": recipients}

    raise ValueError(f"Unknown channel type: {channel_type}")
