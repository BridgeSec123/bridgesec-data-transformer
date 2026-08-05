import logging

import resend
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


def _resolve_recipients(tenant_id: str) -> list[str]:
    """
    Recipients come from enabled email notification_channels in Supabase.
    Falls back to tenant.alert_email if no channel is configured.
    """
    if tenant_id:
        try:
            from core.utils.supabase_notifications import SupabaseNotificationChannel
            channels = SupabaseNotificationChannel.get_enabled_for_tenant(tenant_id)
            recipients = [
                r
                for ch in channels
                if ch.channel_type == "email"
                for r in (ch.config.get("recipients") or [])
            ]
            if recipients:
                return recipients
        except Exception as e:
            logger.warning(f"[ALERT] Could not fetch email channels from Supabase: {e}")

        try:
            from core.utils.supabase_tenant import SupabaseTenant
            tenant = SupabaseTenant.get_by_id(tenant_id)
            if tenant and tenant.alert_email:
                return [tenant.alert_email]
        except Exception as e:
            logger.warning(f"[ALERT] Could not fetch tenant alert_email: {e}")

    return []


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_diff_alert_email(self, anomalies, current_db, previous_db,
                          tenant_id=None, request_id=None):
    """
    Alert configured recipients when Okta entity record counts drop unexpectedly.

    anomalies — list of dicts:
        [{"entity": str, "previous": int, "current": int, "net_change": int}, ...]
    """
    try:
        recipients = _resolve_recipients(tenant_id)
        if not recipients:
            logger.warning(
                "[ALERT] No email recipients configured — skipping diff alert email",
                extra={
                    "component": "celery",
                    "task_name": "send_diff_alert_email",
                    "request_id": request_id,
                    "tenant_id": tenant_id,
                },
            )
            return {"status": "skipped", "reason": "no_recipients_configured"}

        threshold = getattr(settings, "DIFF_ALERT_THRESHOLD", 50)

        table_rows = "\n".join(
            f"  {a['entity']:<30} {a['previous']:>8}  →  {a['current']:>8}   (net {a['net_change']})"
            for a in anomalies
        )

        subject = (
            f"[BridgeSec Alert] Data anomaly detected — "
            f"{len(anomalies)} entit{'y' if len(anomalies) == 1 else 'ies'} lost {threshold}+ records"
        )
        body = (
            f"BridgeSec detected an unusual drop in Okta data for your tenant.\n\n"
            f"Snapshot :  {current_db}\n"
            f"Compared :  {previous_db}\n"
            f"Threshold:  -{threshold} records\n\n"
            f"{'Entity':<30} {'Previous':>8}       {'Current':>8}   Net change\n"
            f"{'-' * 64}\n"
            f"{table_rows}\n\n"
            f"Please verify the Okta data source and review the full diff report.\n"
        )

        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send({
            "from": settings.DEFAULT_FROM_EMAIL,
            "to": recipients,
            "subject": subject,
            "text": body,
        })

        logger.info(
            "[ALERT] Diff alert email sent",
            extra={
                "component":     "celery",
                "task_name":     "send_diff_alert_email",
                "request_id":    request_id,
                "tenant_id":     tenant_id,
                "recipients":    recipients,
                "anomaly_count": len(anomalies),
            },
        )
        return {"status": "sent", "recipients": recipients, "anomalies": len(anomalies)}

    except Exception as exc:
        logger.exception(
            f"[ALERT] Failed to send diff alert email: {exc}",
            extra={
                "component":  "celery",
                "task_name":  "send_diff_alert_email",
                "request_id": request_id,
                "tenant_id":  tenant_id,
            },
        )
        raise self.retry(exc=exc)
