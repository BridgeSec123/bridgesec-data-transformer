-- Migration 009: per-tenant logo storage
-- Adds logo_bucket_path to tenants so each tenant can configure their own application logo.
-- The actual image file is stored in Supabase Storage; this column holds the bucket-relative path.

ALTER TABLE public.tenants
    ADD COLUMN IF NOT EXISTS logo_bucket_path TEXT,
    ADD COLUMN IF NOT EXISTS logo_url TEXT;
