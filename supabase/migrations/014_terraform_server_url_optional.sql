-- Migration 014: OkTf (Terraform workflow) is one shared instance for every
-- tenant, reached via settings.SERVER_URL — not per-tenant config. Callers
-- (bulk_view.py, import_view.py, cross_tenant_migrate_view.py) no longer read
-- tenant.terraform_server_url. Drop the NOT NULL constraint so new tenants
-- don't have to supply it; existing rows keep whatever value they had.

ALTER TABLE public.tenants
    ALTER COLUMN terraform_server_url DROP NOT NULL;
