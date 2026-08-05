"""
Slack channel — POSTs a Block Kit message to the tenant's configured webhook URL.

Runs inside the dedicated Celery notification worker (never blocks bulk fetch workers).
Raises on HTTP error so Celery can retry (max_retries=3, 60s backoff in tasks.py).
"""
import logging

import requests

from core.notifications.channels.base import BaseChannel

logger = logging.getLogger(__name__)

# Severity → Slack sidebar colour
_COLOUR = {
    "info":     "#36a64f",   # green
    "warning":  "#f0ad4e",   # amber
    "error":    "#d9534f",   # red
    "critical": "#7b0000",   # dark red
}

# Severity → emoji prefix
_EMOJI = {
    "info":     ":white_check_mark:",
    "warning":  ":warning:",
    "error":    ":x:",
    "critical": ":rotating_light:",
}



class SlackChannel(BaseChannel):

    def send(self, event_type, severity, title, body, tenant_id,
             tenant_label=None, user_id=None, metadata=None, channel_config=None):

        webhook_url = (channel_config or {}).get("webhook_url")
        if not webhook_url:
            logger.error(f"SlackChannel: no webhook_url configured for tenant {tenant_id}")
            return

        emoji  = _EMOJI.get(severity, ":bell:")
        colour = _COLOUR.get(severity, "#36a64f")

        # Build a simple Block Kit attachment
        payload = {
            "attachments": [
                {
                    "color": colour,
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"{emoji} *{title}*\n{body}",
                            },
                        },
                        {
                            "type": "context",
                            "elements": [
                                {
                                    "type": "mrkdwn",
                                    "text": (
                                        f"*Severity:* {severity.upper()}  |  "
                                        f"*Event:* `{event_type}`  |  "
                                        f"*Tenant:* `{tenant_label or tenant_id}`"
                                    ),
                                }
                            ],
                        },
                    ],
                }
            ]
        }

        resp = requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info(f"SlackChannel delivered {event_type} for tenant {tenant_id} — HTTP {resp.status_code}")
