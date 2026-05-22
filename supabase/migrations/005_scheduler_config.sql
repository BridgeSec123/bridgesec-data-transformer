-- Migration 005: Scheduler configuration columns on the tenants table.
--
-- These four columns store the nightly bulk-backup schedule for each tenant.
-- In single-tenant mode (MULTI_TENANCY_ENABLED=False) the values come from
-- .env (SCHEDULER_HOUR / SCHEDULER_ENABLED) and these columns are unused.
--
-- scheduler_enabled  — toggle the scheduled run on/off without touching Celery
-- scheduler_hour     — UTC hour to execute (0-23); Beat fires every hour, task self-skips
-- scheduler_minute   — minute within that hour (default 0)
-- scheduler_timezone — display label only; execution is always UTC

ALTER TABLE public.tenants
    ADD COLUMN IF NOT EXISTS scheduler_enabled  BOOLEAN  NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS scheduler_hour     SMALLINT NOT NULL DEFAULT 0
        CHECK (scheduler_hour  BETWEEN 0 AND 23),
    ADD COLUMN IF NOT EXISTS scheduler_minute   SMALLINT NOT NULL DEFAULT 0
        CHECK (scheduler_minute BETWEEN 0 AND 59),
    ADD COLUMN IF NOT EXISTS scheduler_timezone TEXT     NOT NULL DEFAULT 'UTC';
