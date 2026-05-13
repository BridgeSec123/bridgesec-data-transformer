-- ============================================================
-- Migration 002: Per-tenant Supabase credentials
-- Run in Supabase SQL editor after 001_rbac_schema.sql.
--
-- Adds optional supabase_url / supabase_key columns to tenants.
-- When populated, the Django app connects to that Supabase instance
-- for this tenant instead of the master one (from .env).
-- When NULL, the master Supabase is used (backward-compatible default).
-- ============================================================

ALTER TABLE public.tenants
    ADD COLUMN IF NOT EXISTS supabase_url TEXT,
    ADD COLUMN IF NOT EXISTS supabase_key TEXT;
