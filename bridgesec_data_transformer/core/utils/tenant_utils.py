"""
Tenant resolution utilities for multi-tenant support.

All functions are no-ops (or return None) when MULTI_TENANCY_ENABLED=False.
Tenant data is stored in Supabase (not MongoDB).
MongoDB connections in this module are only for per-tenant snapshot databases.
"""
import logging
from datetime import datetime

from django.conf import settings
from pymongo import MongoClient

logger = logging.getLogger(__name__)

# Module-level connection pool: keyed by mongo_uri so connections are reused
_tenant_clients: dict = {}


def get_tenant_by_id(tenant_id: str):
    """
    Load a Tenant from Supabase by its UUID.
    Returns None if not found or multi-tenancy is disabled.
    """
    if not getattr(settings, "MULTI_TENANCY_ENABLED", False):
        return None
    try:
        from core.utils.supabase_tenant import SupabaseTenant
        return SupabaseTenant.get_by_id(str(tenant_id))
    except Exception as e:
        logger.warning(f"get_tenant_by_id({tenant_id}) failed: {e}")
        return None


def get_tenant_by_okta_domain(domain: str):
    """
    Load a Tenant from Supabase by its okta_domain field.
    Returns None if not found or multi-tenancy is disabled.
    """
    if not getattr(settings, "MULTI_TENANCY_ENABLED", False):
        return None
    try:
        from core.utils.supabase_tenant import SupabaseTenant
        return SupabaseTenant.get_by_okta_domain(domain)
    except Exception as e:
        logger.warning(f"get_tenant_by_okta_domain({domain}) failed: {e}")
        return None


def get_dynamic_db_for_tenant(tenant) -> str:
    """
    Return the snapshot DB name for *this* tenant right now.
    Format: "<mongo_db_prefix>_<YYYY-MM-DDTHHMM>"
    MongoDB is used only for snapshot storage.
    """
    now = datetime.utcnow()
    return f"{tenant.mongo_db_prefix}_{now:%Y-%m-%dT%H%M}"


def get_tenant_from_request(request):
    """
    Return the SupabaseTenant attached by TenantContextMiddleware, or None.

    Single shared helper imported by all views (BulkEntityViewSet,
    ConfirmDeletionView, etc.) so tenant-resolution behaviour is consistent.
    Returns None when MULTI_TENANCY_ENABLED=False or no tenant on the request.
    """
    if not getattr(settings, "MULTI_TENANCY_ENABLED", False):
        return None
    return getattr(request, "_tenant", None)


def get_request_mongo_client(request) -> MongoClient:
    """
    Convenience: resolve tenant from request and return the correct MongoClient.
    Falls back to the global settings.MONGO_CLIENT when no tenant is present.
    """
    tenant = get_tenant_from_request(request)
    if tenant:
        return get_mongo_client_for_tenant(tenant)
    from django.conf import settings as _s
    return _s.MONGO_CLIENT


def get_mongo_client_for_tenant(tenant) -> MongoClient:
    """
    Return a MongoClient for the given tenant's snapshot database,
    reusing connections per URI.
    Falls back to settings.MONGO_URI when the tenant has no mongo_uri configured.
    """
    from django.conf import settings as _s
    uri = tenant.mongo_uri or _s.MONGO_URI
    if not uri:
        raise ValueError(f"No MongoDB URI available for tenant '{tenant.name}' and no global MONGO_URI configured.")
    if uri not in _tenant_clients:
        _tenant_clients[uri] = MongoClient(uri)
        source = "tenant-specific" if tenant.mongo_uri else "global fallback"
        logger.info(f"Created new MongoClient for tenant '{tenant.name}' using {source} URI (prefix: {uri[:30]}...)")
    return _tenant_clients[uri]


def is_super_admin(user) -> bool:
    """Return True if the user has the super_admin role."""
    return "super_admin" in (getattr(user, "roles", None) or [])


def get_all_tenants() -> list:
    """
    Fetch all active tenants from Supabase.
    Used by super admin cross-tenant views to iterate every tenant's MongoDB.
    """
    try:
        from core.utils.supabase_tenant import SupabaseTenant
        tenants, _ = SupabaseTenant.list_all(active_only=True, page=1, page_size=1000)
        return tenants
    except Exception as e:
        logger.warning(f"get_all_tenants() failed: {e}")
        return []


def resolve_tenant_for_request(request):
    """
    Resolve the active tenant for a request with super-admin awareness.

    - Regular users/tenant_admin: returns request._tenant (set by middleware from JWT).
    - Super admin + ?tenant_id= present: resolves and returns that specific tenant.
    - Super admin without ?tenant_id=: returns None — caller handles cross-tenant or default.
    - Multi-tenancy disabled: always returns None.
    """
    if not getattr(settings, "MULTI_TENANCY_ENABLED", False):
        return None

    user = getattr(request, "user", None)
    if is_super_admin(user):
        tenant_id = request.query_params.get("tenant_id")
        if tenant_id:
            return get_tenant_by_id(tenant_id)
        return None

    return getattr(request, "_tenant", None)


def ensure_mongo_connection_for_tenant(tenant, db_name: str):
    """
    Register a MongoEngine alias for this tenant's snapshot DB so that
    MongoEngine models can be used with .using(alias).
    Falls back to settings.MONGO_URI when the tenant has no mongo_uri configured.

    Alias format: "tenant_{tenant_id}_{db_name}"
    """
    try:
        import mongoengine
        from django.conf import settings as _s
        uri = tenant.mongo_uri or _s.MONGO_URI
        if not uri:
            raise ValueError(f"No MongoDB URI available for tenant '{tenant.name}' and no global MONGO_URI configured.")
        alias = f"tenant_{tenant.id}_{db_name}"
        if alias not in mongoengine.connection._get_connection_settings():
            mongoengine.connect(db=db_name, host=uri, alias=alias)
            source = "tenant-specific" if tenant.mongo_uri else "global fallback"
            logger.info(f"Registered MongoEngine alias '{alias}' for tenant '{tenant.name}' using {source} URI")
        return alias
    except Exception as e:
        logger.warning(f"ensure_mongo_connection_for_tenant failed for '{tenant.name}': {e}")
        return None
