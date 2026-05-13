-- ============================================================
-- Migration 001: RBAC schema
-- Run this in the Supabase SQL editor before deploying.
-- All application data lives here; MongoDB is snapshot-only.
-- ============================================================

-- ── 1. users — replace single role with JSONB roles array ────────────────
ALTER TABLE public.users DROP COLUMN IF EXISTS role;
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS roles JSONB NOT NULL DEFAULT '["user"]';

CREATE INDEX IF NOT EXISTS idx_users_roles
    ON public.users USING gin(roles);

-- ── 2. tenants ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.tenants (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                 TEXT UNIQUE NOT NULL,
    okta_domain          TEXT UNIQUE NOT NULL,
    okta_client_id       TEXT NOT NULL,
    okta_client_secret   TEXT NOT NULL,
    okta_issuer          TEXT NOT NULL,
    mongo_uri            TEXT NOT NULL,
    mongo_db_prefix      TEXT NOT NULL,
    terraform_server_url TEXT NOT NULL,
    terraform_state_path TEXT NOT NULL,
    service_client_id    TEXT,
    service_private_key  TEXT,
    service_scopes       TEXT,
    is_active            BOOLEAN NOT NULL DEFAULT TRUE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── 3. roles ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.roles (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name         TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    description  TEXT,
    is_system    BOOLEAN NOT NULL DEFAULT FALSE,
    -- NULL = global role; non-NULL = visible only within that tenant
    tenant_id    UUID REFERENCES public.tenants(id) ON DELETE CASCADE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by   TEXT
);

CREATE INDEX IF NOT EXISTS idx_roles_tenant ON public.roles(tenant_id);

-- ── 4. activity_logs ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.activity_logs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID REFERENCES public.tenants(id) ON DELETE SET NULL,
    user_email  TEXT NOT NULL,
    -- action values: login | logout | bulk_fetch | restore | create | delete | view
    action      TEXT NOT NULL,
    entity_name TEXT,
    db_name     TEXT,
    status      TEXT,
    ip_address  TEXT,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    details     JSONB
);

CREATE INDEX IF NOT EXISTS idx_logs_tenant ON public.activity_logs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_logs_ts     ON public.activity_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_logs_action ON public.activity_logs(action);

-- ── 5. policy_rules ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.policy_rules (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL DEFAULT '',
    description TEXT,
    role        TEXT NOT NULL,
    entity      TEXT NOT NULL,
    action      TEXT NOT NULL,
    effect      TEXT NOT NULL CHECK (effect IN ('allow', 'deny')),
    conditions  JSONB,
    rego_source TEXT,
    created_by  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_policy_role ON public.policy_rules(role);
