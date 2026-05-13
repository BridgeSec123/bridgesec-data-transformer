-- Migration 003: Add tenant_id to policy_rules for per-tenant policy scoping.
--
-- Rules where tenant_id IS NULL are global (created by super_admin) and apply
-- to all tenants. Rules where tenant_id is set only apply to that specific tenant.

ALTER TABLE public.policy_rules
    ADD COLUMN IF NOT EXISTS tenant_id TEXT DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_policy_rules_tenant
    ON public.policy_rules(tenant_id);

COMMENT ON COLUMN public.policy_rules.tenant_id IS
    'NULL = global policy (super_admin created, applies to all tenants). '
    'Set = applies only to the specified tenant.';
