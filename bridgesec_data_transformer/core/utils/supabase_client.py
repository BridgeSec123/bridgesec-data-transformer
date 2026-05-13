"""
Supabase client helpers.

- get_supabase_client()          → master Supabase client (from .env)
- get_supabase_client_for_tenant(tenant) → per-tenant client when the tenant
  row carries its own supabase_url / supabase_key; falls back to master client.
"""
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

_client = None
# Pool of per-tenant clients keyed by (supabase_url, supabase_key)
_tenant_clients: dict = {}


def get_supabase_client():
    """Return the shared master Supabase client, creating it on first call."""
    global _client
    if _client is None:
        from supabase import create_client
        url = settings.SUPABASE_URL
        key = settings.SUPABASE_KEY
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")
        _client = create_client(url, key)
        logger.info("Supabase client initialized")
    return _client


def get_supabase_client_for_tenant(tenant):
    """
    Return a Supabase client for the given tenant.

    If the tenant row has its own supabase_url and supabase_key, a dedicated
    client is created (and pooled by URL+key). Otherwise the master client is
    returned so callers never need to null-check.
    """
    url = getattr(tenant, "supabase_url", None)
    key = getattr(tenant, "supabase_key", None)
    if not url or not key:
        return get_supabase_client()

    cache_key = (url, key)
    if cache_key not in _tenant_clients:
        from supabase import create_client
        _tenant_clients[cache_key] = create_client(url, key)
        logger.info(f"Supabase client initialized for tenant '{getattr(tenant, 'name', '?')}'")
    return _tenant_clients[cache_key]
