"""
Microsoft Teams channel — POSTs a MessageCard to the tenant's incoming webhook URL.

Runs inside the dedicated Celery notification worker.
Raises on HTTP error so Celery can retry.
"""
import logging

import requests

from core.notifications.channels.base import BaseChannel

logger = logging.getLogger(__name__)

_THEME_COLOUR = {
    "info":     "0076D7",   # blue
    "warning":  "FFA500",   # orange
    "error":    "D9534F",   # red
    "critical": "7B0000",   # dark red
}


class TeamsChannel(BaseChannel):

    def send(self, event_type, severity, title, body, tenant_id,
             tenant_label=None, user_id=None, metadata=None, channel_config=None):

        webhook_url = (channel_config or {}).get("webhook_url")
        if not webhook_url:
            logger.error(f"TeamsChannel: no webhook_url configured for tenant {tenant_id}")
            return

        colour = _THEME_COLOUR.get(severity, "0076D7")

        payload = {
            "@type":      "MessageCard",
            "@context":   "http://schema.org/extensions",
            "themeColor": colour,
            "summary":    title,
            "sections": [
                {
                    "activityTitle":    f"**{title}**",
                    "activitySubtitle": f"Severity: {severity.upper()}  |  Event: `{event_type}`",
                    "activityText":     body,
                    "facts": [
                        {"name": "Tenant",    "value": tenant_label or str(tenant_id)},
                        {"name": "Severity",  "value": severity.upper()},
                        {"name": "Event",     "value": event_type},
                    ],
                    "markdown": True,
                }
            ],
        }

        resp = requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info(f"TeamsChannel delivered {event_type} for tenant {tenant_id} — HTTP {resp.status_code}")
