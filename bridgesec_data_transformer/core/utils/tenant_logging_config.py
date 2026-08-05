"""
Per-tenant logging backend lookup — single source of truth for both the
write-side TenantLogRouter and the read-side log reader factory, so a
tenant's logs are always written to and read from the same place.

Elasticsearch/Splunk/Loki are each ONE shared instance (see settings.py:
ELASTICSEARCH_URL / SPLUNK_* / LOKI_*) — a tenant only picks WHICH backend,
never its own connection details. So the only per-tenant value is the
backend name itself.

TTL-cached (reuses MAPPINGS_CACHE_TTL_SEC) so the hot log-emit path doesn't
hit Supabase per log line. Falls back to 'elasticsearch' whenever
multi-tenancy is off, the tenant is unknown, or Supabase is unreachable.
"""
import logging
import time

logger = logging.getLogger(__name__)

_DEFAULT_BACKEND = "elasticsearch"
_cache: dict = {}  # tenant_id -> (backend, expires_at)


def _ttl_seconds() -> int:
    from django.conf import settings
    return getattr(settings, "MAPPINGS_CACHE_TTL_SEC", 300)


def get_logging_backend(tenant_id) -> str:
    """Return the logging backend name ('elasticsearch'/'splunk'/'loki') for tenant_id."""
    if not tenant_id:
        return _DEFAULT_BACKEND

    cached = _cache.get(tenant_id)
    if cached and cached[1] > time.monotonic():
        return cached[0]

    try:
        from django.conf import settings
        if not getattr(settings, "MULTI_TENANCY_ENABLED", False):
            return _DEFAULT_BACKEND

        from core.utils.tenant_utils import get_tenant_by_id
        tenant = get_tenant_by_id(tenant_id)
        backend = getattr(tenant, "logging_backend", None) or _DEFAULT_BACKEND
    except Exception as e:
        logger.warning(f"get_logging_backend({tenant_id}) failed, defaulting to elasticsearch: {e}")
        backend = _DEFAULT_BACKEND

    _cache[tenant_id] = (backend, time.monotonic() + _ttl_seconds())
    return backend


def invalidate_logging_backend_cache(tenant_id):
    """Drop the cached entry so the next lookup re-reads Supabase. Call after a tenant PUT."""
    _cache.pop(tenant_id, None)
