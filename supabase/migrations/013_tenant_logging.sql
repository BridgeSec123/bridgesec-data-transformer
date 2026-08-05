-- Migration 013: Per-tenant logging backend configuration.
--
-- logging_backend — which log sink this tenant's application logs are written to
--                    and read from: 'elasticsearch' | 'splunk' | 'loki'
-- logging_config   — backend-specific connection details (HEC token/URL for Splunk,
--                     push/query URLs for Loki). Empty for elasticsearch, which uses
--                     the global ELASTICSEARCH_URL env var.

ALTER TABLE public.tenants
    ADD COLUMN IF NOT EXISTS logging_backend TEXT NOT NULL DEFAULT 'elasticsearch'
        CHECK (logging_backend IN ('elasticsearch', 'splunk', 'loki')),
    ADD COLUMN IF NOT EXISTS logging_config  JSONB NOT NULL DEFAULT '{}'::jsonb;
