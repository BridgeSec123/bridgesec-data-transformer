-- Migration 008: Per-tenant last-run guard for the scheduled bulk fetch.
--
-- The scheduled snapshot DB name is granular to the minute
-- (bridgesec_YYYY-MM-DDTHHMM), so if a tenant is dispatched twice within the same
-- minute — e.g. Beat and the APScheduler fallback both firing, a missed-tick
-- catch-up, or a worker retry — both runs share one db_name and corrupt that
-- snapshot. This column lets the scheduler atomically claim a slot before
-- dispatching, so a tenant runs at most once per slot.
--
-- last_scheduled_run — opaque slot key in the tenant's timezone, e.g.
--                      "2026-06-05T0800". Set via a conditional UPDATE
--                      (see SupabaseTenant.try_claim_scheduled_slot); the caller
--                      that wins the row update is the only one that dispatches.

ALTER TABLE public.tenants
    ADD COLUMN IF NOT EXISTS last_scheduled_run TEXT;
