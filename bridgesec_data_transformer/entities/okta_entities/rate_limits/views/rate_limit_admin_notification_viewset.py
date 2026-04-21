import logging

from entities.views.base_view import BaseEntityViewSet
from entities.okta_entities.rate_limits.rate_limit_models import RateLimitAdminNotification
from entities.okta_entities.rate_limits.rate_limit_serializer import RateLimitAdminNotificationSerializer

logger = logging.getLogger(__name__)


class RateLimitAdminNotificationViewSet(BaseEntityViewSet):
    okta_endpoint = "/api/v1/rate-limit-settings/admin-notifications"
    entity_type = "rate_limit_admin_notifications"
    serializer_class = RateLimitAdminNotificationSerializer
    model = RateLimitAdminNotification

    def extract_data(self, okta_data):
        items = okta_data if isinstance(okta_data, list) else [okta_data]
        formatted_data = []
        for item in items:
            if not isinstance(item, dict):
                logger.warning("Skipping invalid record (not a dict): %s", item)
                continue
            formatted_data.append({
                "notification_id": item.get("id", ""),
                "notifications_enabled": str(item.get("notificationsEnabled", "")),
            })
        logger.info("Extracted %d Rate Limit Admin Notification records", len(formatted_data))
        return formatted_data
