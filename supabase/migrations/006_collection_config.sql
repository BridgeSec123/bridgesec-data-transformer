-- Per-tenant enable/disable overrides at the collection level.
-- Each row disables (or re-enables) a specific MongoDB collection within an entity group
-- for a given tenant.
-- No row for (tenant_id, entity_name, collection_name) → collection inherits the parent
-- entity's enabled value (safe default).
-- tenant_id = NULL → global config used in single-tenancy mode.

CREATE TABLE IF NOT EXISTS tenant_collection_config (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID REFERENCES tenants(id) ON DELETE CASCADE,
    entity_name     TEXT NOT NULL REFERENCES entity_catalog(name) ON DELETE CASCADE,
    collection_name TEXT NOT NULL,
    enabled         BOOLEAN DEFAULT TRUE,
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_by      TEXT
);

-- Two partial unique indexes (same pattern as tenant_entity_config)
-- because PostgreSQL treats NULL != NULL in unique constraints.

CREATE UNIQUE INDEX IF NOT EXISTS tcc_tenant_unique
    ON tenant_collection_config(tenant_id, entity_name, collection_name)
    WHERE tenant_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS tcc_global_unique
    ON tenant_collection_config(entity_name, collection_name)
    WHERE tenant_id IS NULL;

CREATE INDEX IF NOT EXISTS tcc_tenant_idx ON tenant_collection_config(tenant_id);
