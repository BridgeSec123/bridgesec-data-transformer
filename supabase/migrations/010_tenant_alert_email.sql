-- Migration 010: per-tenant alert email for diff anomaly notifications
-- Stores the recipient address for automated data-loss alerts on each tenant.
-- Configured via PUT /api/tenants/<id>/ {"alert_email": "admin@company.com"} (super-admin only).

ALTER TABLE public.tenants
    ADD COLUMN IF NOT EXISTS alert_email TEXT;
