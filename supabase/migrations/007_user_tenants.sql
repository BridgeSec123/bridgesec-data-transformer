-- Migration 007: username on users + user_tenants junction table
-- Run in Supabase project: aeshytfxhafsscliggkh (https://aeshytfxhafsscliggkh.supabase.co)
-- Run AFTER 001_rbac_schema.sql

-- ── 1. username column on users ───────────────────────────────────────────
-- Primary login identifier; unique across all tenants.
-- NULL allowed for existing rows (backfill manually or via admin UI if needed).
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS username TEXT UNIQUE;

CREATE INDEX IF NOT EXISTS idx_users_username ON public.users(username);

-- ── 2. user_tenants junction table ────────────────────────────────────────
-- Maps users to the tenants they can access, with a per-tenant role.
-- One user can appear multiple times (once per tenant they belong to).
-- Deleting a user or tenant cascades automatically.
CREATE TABLE IF NOT EXISTS public.user_tenants (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    tenant_id   UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    role        TEXT NOT NULL DEFAULT 'user',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, tenant_id)
);

CREATE INDEX IF NOT EXISTS idx_user_tenants_user   ON public.user_tenants(user_id);
CREATE INDEX IF NOT EXISTS idx_user_tenants_tenant ON public.user_tenants(tenant_id);
