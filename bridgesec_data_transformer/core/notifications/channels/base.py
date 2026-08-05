"""
Base channel interface.

Every channel driver (dashboard, slack, teams, email) extends BaseChannel
and implements send(). The router calls send() — it never knows which
channel it's talking to. Adding a new channel = write one class, nothing else.
"""
from abc import ABC, abstractmethod


class BaseChannel(ABC):

    @abstractmethod
    def send(
        self,
        event_type: str,
        severity: str,
        title: str,
        body: str,
        tenant_id: str,
        tenant_label: str,
        user_id: str | None,
        metadata: dict,
        channel_config: dict,
    ) -> None:
        """
        Deliver the notification through this channel.

        Args:
            event_type:     e.g. "bulk_fetch_failed"
            severity:       "info" | "warning" | "error" | "critical"
            title:          short human-readable label
            body:           detail text
            tenant_id:      scopes the notification to the right tenant
            user_id:        target user; None = broadcast to all tenant users
            metadata:       arbitrary dict (db_name, entity_name, counts, etc.)
            channel_config: row from notification_channels.config for this channel
        """
