-- Entity catalog: global master list of all Okta entity groups
-- One row per top-level entry in ENTITY_VIEWSETS / FULL_ENTITY_REGISTRY
-- is_active=TRUE  → available for backup selection
-- is_active=FALSE → visible in UI as "not yet available" (commented-out entities)

CREATE TABLE IF NOT EXISTS entity_catalog (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name         TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    category     TEXT NOT NULL,
    description  TEXT,
    collections  JSONB DEFAULT '[]',
    is_active    BOOLEAN DEFAULT FALSE,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Per-tenant enable/disable overrides.
-- No row for (tenant_id, entity_name) → entity is enabled by default.
-- tenant_id = NULL → global config used in single-tenancy mode.

CREATE TABLE IF NOT EXISTS tenant_entity_config (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID REFERENCES tenants(id) ON DELETE CASCADE,
    entity_name TEXT NOT NULL REFERENCES entity_catalog(name) ON DELETE CASCADE,
    enabled     BOOLEAN DEFAULT TRUE,
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_by  TEXT
);

-- Two partial unique indexes instead of a single UNIQUE(tenant_id, entity_name)
-- because PostgreSQL treats NULL != NULL in unique constraints.

CREATE UNIQUE INDEX IF NOT EXISTS tec_tenant_unique
    ON tenant_entity_config(tenant_id, entity_name)
    WHERE tenant_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS tec_global_unique
    ON tenant_entity_config(entity_name)
    WHERE tenant_id IS NULL;

CREATE INDEX IF NOT EXISTS tec_tenant_idx ON tenant_entity_config(tenant_id);
