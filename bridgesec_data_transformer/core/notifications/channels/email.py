"""
Email channel — sends via Resend API.

Runs inside the dedicated Celery notification worker.
Raises on failure so Celery can retry.
Recipients are resolved from channel_config["recipients"] (Supabase notification_channels).
"""
import logging

import resend
from django.conf import settings

from core.notifications.channels.base import BaseChannel

logger = logging.getLogger(__name__)

# Severity → badge colour (inline CSS so Gmail renders it)
_SEVERITY_COLORS = {
    "info":     {"bg": "#e8f4fd", "text": "#1a6fa8", "border": "#90caf9"},
    "warning":  {"bg": "#fff8e1", "text": "#b45309", "border": "#fcd34d"},
    "error":    {"bg": "#fff0f0", "text": "#c0392b", "border": "#f9a8a8"},
    "critical": {"bg": "#fdf2f8", "text": "#7b2d8b", "border": "#d39de8"},
}

_SEVERITY_ICONS = {
    "info":     "ℹ️",
    "warning":  "⚠️",
    "error":    "❌",
    "critical": "🚨",
}

_EVENT_LABELS = {
    "bulk_fetch_completed":             "Bulk Fetch Completed",
    "bulk_fetch_failed":                "Bulk Fetch Failed",
    "bulk_fetch_partial":               "Bulk Fetch Partially Completed",
    "restore_completed":                "Restore Completed",
    "restore_failed":                   "Restore Failed",
    "create_completed":                 "Create Completed",
    "deletion_confirmed":               "Deletion Confirmed",
    "deletion_failed":                  "Deletion Failed",
    "anomaly_detected":                 "Anomaly Detected",
    "diff_task_failed":                 "Change Detection Failed",
    "cross_tenant_migration_completed": "Cross-Tenant Migration Completed",
    "cross_tenant_migration_failed":    "Cross-Tenant Migration Failed",
    "user_login":                       "User Login",
    "user_created":                     "User Added",
    "user_removed":                     "User Removed",
    "user_role_escalated":              "User Role Escalated",
    "policy_created":                   "Policy Created",
    "policy_updated":                   "Policy Updated",
    "policy_deleted":                   "Policy Deleted",
}

_METADATA_LABELS = {
    "entity":           "Entity",
    "restored_count":   "Restored Count",
    "deleted_count":    "Deleted Count",
    "created_count":    "Created Count",
    "by":               "Performed By",
    "db_name":          "Snapshot",
    "successful":       "Successful Groups",
    "failed":           "Failed Groups",
    "duration_ms":      "Duration",
    "request_id":       "Request ID",
    "error":            "Error",
}


def _format_value(key, val):
    if key == "duration_ms" and isinstance(val, (int, float)):
        secs = val / 1000
        return f"{secs:.1f}s"
    return str(val)


def _build_html(event_type, severity, title, body, tenant_id, metadata, tenant_label=None):
    colors = _SEVERITY_COLORS.get(severity, _SEVERITY_COLORS["info"])
    icon   = _SEVERITY_ICONS.get(severity, "ℹ️")
    label  = _EVENT_LABELS.get(event_type, event_type.replace("_", " ").title())

    # Build metadata rows — skip internal/noisy fields
    skip_keys = {"task", "request_id"}
    meta_rows = ""
    for key, val in (metadata or {}).items():
        if key in skip_keys or val is None:
            continue
        display_label = _METADATA_LABELS.get(key, key.replace("_", " ").title())
        display_val   = _format_value(key, val)
        meta_rows += f"""
        <tr>
          <td style="padding:8px 12px;color:#6b7280;font-size:13px;white-space:nowrap;
                     border-bottom:1px solid #f3f4f6;">{display_label}</td>
          <td style="padding:8px 12px;color:#111827;font-size:13px;
                     border-bottom:1px solid #f3f4f6;"><strong>{display_val}</strong></td>
        </tr>"""

    meta_section = ""
    if meta_rows:
        meta_section = f"""
      <table width="100%" cellpadding="0" cellspacing="0"
             style="border:1px solid #e5e7eb;border-radius:6px;border-collapse:collapse;
                    margin-top:20px;">
        {meta_rows}
      </table>"""

    body_section = ""
    if body:
        body_section = f"""
      <p style="margin:16px 0 0;color:#374151;font-size:14px;line-height:1.6;">{body}</p>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f9fafb;font-family:-apple-system,BlinkMacSystemFont,
             'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;padding:32px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0"
             style="background:#ffffff;border-radius:8px;
                    box-shadow:0 1px 3px rgba(0,0,0,.08);overflow:hidden;max-width:600px;">

        <!-- Header -->
        <tr>
          <td style="background:#0f172a;padding:20px 28px;">
            <span style="color:#ffffff;font-size:18px;font-weight:700;letter-spacing:-.3px;">
              🔒 BridgeSec
            </span>
            <span style="color:#94a3b8;font-size:13px;margin-left:10px;">Security Platform</span>
          </td>
        </tr>

        <!-- Severity badge + title -->
        <tr>
          <td style="padding:28px 28px 0;">
            <span style="display:inline-block;padding:4px 10px;border-radius:99px;
                         font-size:12px;font-weight:600;letter-spacing:.4px;
                         background:{colors['bg']};color:{colors['text']};
                         border:1px solid {colors['border']};">
              {icon}&nbsp;&nbsp;{severity.upper()}
            </span>
            <h1 style="margin:12px 0 0;color:#111827;font-size:20px;font-weight:700;
                       line-height:1.3;">{title}</h1>
            <p style="margin:4px 0 0;color:#6b7280;font-size:13px;">{label}</p>
            {body_section}
            {meta_section}
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="padding:24px 28px 28px;border-top:1px solid #f3f4f6;margin-top:24px;">
            <p style="margin:16px 0 0;color:#9ca3af;font-size:12px;">
              This notification was sent by BridgeSec for tenant
              <code style="background:#f3f4f6;padding:1px 5px;border-radius:3px;
                           font-size:11px;">{tenant_label or tenant_id}</code>.
              <br>You are receiving this because you are configured as a notification recipient.
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


class EmailChannel(BaseChannel):

    def send(self, event_type, severity, title, body, tenant_id,
             tenant_label=None, user_id=None, metadata=None, channel_config=None):

        recipients = (channel_config or {}).get("recipients") or []
        if not recipients:
            logger.error(f"EmailChannel: no recipients configured for tenant {tenant_id}")
            return

        subject = f"[BridgeSec] {title}"

        html = _build_html(event_type, severity, title, body, tenant_id, metadata, tenant_label=tenant_label)

        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send({
            "from":    settings.DEFAULT_FROM_EMAIL,
            "to":      recipients,
            "subject": subject,
            "html":    html,
        })
        logger.info(
            f"EmailChannel delivered {event_type} for tenant {tenant_id} to {recipients}"
        )
