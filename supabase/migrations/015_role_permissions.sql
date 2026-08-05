-- Migration 015: Role permission lists (replaces ini-based RBAC).
--
-- permissions — list of named permission strings this role grants, e.g.
--               ["trigger_bulk_fetch", "view_db_map", "restore_data"].
--               Checked by core/permissions/rbac_permission.py:RolePermission
--               against each endpoint's @require_permission(...) tag.

ALTER TABLE public.roles
    ADD COLUMN IF NOT EXISTS permissions JSONB NOT NULL DEFAULT '[]'::jsonb;
