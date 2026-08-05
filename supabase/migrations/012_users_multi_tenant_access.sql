-- Migration 012: multi-tenant users table restructure + app_access_enabled
-- Run in Supabase project after 011 (or 010 if 011 does not exist yet).
--
-- Changes:
--   1. Drop single-column UNIQUE on email and username
--      (same person now has one row per tenant; email uniqueness moves to composite)
--   2. Add app_access_enabled BOOLEAN — controls per-tenant application login access
--   3. Mark TRUE for rows that already have a matching user_tenants entry
--   4. Add UNIQUE(email, tenant_id) composite constraint
--   5. Indexes for fast cross-tenant email lookups

-- ── 1. Drop old single-column unique constraints ──────────────────────────────
ALTER TABLE public.users DROP CONSTRAINT IF EXISTS users_email_key;
ALTER TABLE public.users DROP CONSTRAINT IF EXISTS users_username_key;

-- ── 2. Add app_access_enabled — default FALSE; only confirmed members get TRUE ─
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS app_access_enabled BOOLEAN NOT NULL DEFAULT FALSE;

-- ── 3. Mark TRUE for every users row that has a matching user_tenants entry ────
--    user_tenants is the source of truth for current authorized memberships.
UPDATE public.users u
SET app_access_enabled = TRUE
FROM public.user_tenants ut
WHERE ut.user_id = u.id
  AND ut.tenant_id::TEXT = u.tenant_id;

-- ── 4. Composite unique: one row per person per tenant ────────────────────────
ALTER TABLE public.users
    ADD CONSTRAINT uq_users_email_tenant UNIQUE (email, tenant_id);

-- ── 5. Indexes ────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_app_access ON public.users(email, app_access_enabled);
