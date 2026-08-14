"""
Tenant resolution utilities for multi-tenant support.

All functions are no-ops (or return None) when MULTI_TENANCY_ENABLED=False.
Tenant data is stored in Supabase (not MongoDB).
MongoDB connections in this module are only for per-tenant snapshot databases.
"""
import logging
from contextvars import ContextVar
from datetime import datetime
from typing import Optional

from django.conf import settings
from pymongo import MongoClient

logger = logging.getLogger(__name__)

# Stores the current SupabaseTenant object for the duration of a request/task.
# Set by CustomJWTAuthentication (HTTP) and Celery task entry points (background).
# Read by TenantContextFilter before each ES log record is emitted.
_current_tenant_ctx: ContextVar[Optional[object]] = ContextVar("current_tenant", default=None)


def set_current_tenant(tenant) -> None:
    """Store the SupabaseTenant object (or None) for the current request/task context."""
    _current_tenant_ctx.set(tenant)


def get_current_tenant():
    """Return the current SupabaseTenant object, or None if not set."""
    return _current_tenant_ctx.get()


# Stores the current authenticated user's email for the duration of a request/task.
# Set by CustomJWTAuthentication (HTTP) and Celery task entry points (background).
# Read by UserContextFilter before each log record is emitted.
_current_user_ctx: ContextVar[Optional[str]] = ContextVar("current_user", default=None)


def set_current_user(email) -> None:
    """Store the authenticated user's email for the current request/task context."""
    _current_user_ctx.set(email)


def get_current_user():
    """Return the current user's email, or None if not set."""
    return _current_user_ctx.get()

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
    Return the SupabaseTenant for the current request, or None.

    Single shared helper imported by all views (BulkEntityViewSet,
    ConfirmDeletionView, etc.) so tenant-resolution behaviour is consistent.
    Returns None when MULTI_TENANCY_ENABLED=False or no tenant on the request.

    CustomJWTAuthentication already resolves the tenant and attaches it as
    request._tenant during authentication — reuse that instead of hitting
    Supabase again for the same tenant on every call within the same request.
    Falls back to a fresh lookup by request._tenant_id when _tenant isn't set
    (e.g. some Okta-token auth paths don't always attach it).
    """
    if not getattr(settings, "MULTI_TENANCY_ENABLED", False):
        return None
    cached_tenant = getattr(request, "_tenant", None)
    if cached_tenant:
        return cached_tenant
    tenant_id = getattr(request, "_tenant_id", None)
    if tenant_id:
        return get_tenant_by_id(tenant_id)
    return None


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


def get_client_for_uri(uri: str) -> MongoClient:
    """
    Return a MongoClient for the given URI, reusing connections per URI string.

    Use this when you already have the URI (e.g. from a Celery task parameter)
    rather than a full SupabaseTenant object.  Shares the same _tenant_clients
    cache as get_mongo_client_for_tenant so connections are never duplicated.
    """
    if uri not in _tenant_clients:
        _tenant_clients[uri] = MongoClient(uri)
        logger.info(f"Created MongoClient for uri prefix: {uri[:30]}...")
    return _tenant_clients[uri]


def get_mongo_client_for_tenant(tenant) -> MongoClient:
    """
    Return a MongoClient for the given tenant's snapshot database,
    reusing connections per URI.
    Uses the tenant's own mongo_uri from Supabase — never silently falls back
    to another tenant's URI so data isolation is guaranteed.
    """
    uri = tenant.mongo_uri
    if not uri:
        raise ValueError(
            f"Tenant '{tenant.name}' has no mongo_uri configured in Supabase. "
            "Set mongo_uri on the tenant record to enable MongoDB access."
        )
    return get_client_for_uri(uri)


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

    - Regular users/tenant_admin: resolves from _tenant_id set by CustomJWTAuthentication.
    - Super admin + ?tenant_id= present: resolves that specific tenant (explicit override).
    - Super admin without ?tenant_id=: falls back to JWT-scoped tenant (same as regular users).
      After a tenant switch the new JWT carries the switched tenant_id, so this correctly
      scopes the super_admin to the tenant they switched into.
    - Multi-tenancy disabled: always returns None.
    """
    if not getattr(settings, "MULTI_TENANCY_ENABLED", False):
        return None

    user = getattr(request, "user", None)
    if is_super_admin(user):
        # Explicit query-param override takes priority (cross-tenant admin operations)
        tenant_id = request.query_params.get("tenant_id")
        if tenant_id:
            return get_tenant_by_id(tenant_id)
        # Fall through to JWT-scoped tenant resolution below

    # Shared path for regular users and super_admin (without query-param override):
    # resolve from request._tenant cached by CustomJWTAuthentication,
    # or load lazily from _tenant_id (JWT claim) on first call.
    tenant = getattr(request, "_tenant", None)
    if tenant is None:
        tenant_id = getattr(request, "_tenant_id", None)
        if tenant_id:
            tenant = get_tenant_by_id(tenant_id)
            request._tenant = tenant
    return tenant


def ensure_mongo_connection_for_tenant(tenant, db_name: str):
    """
    Register a MongoEngine alias for this tenant's snapshot DB so that
    MongoEngine models can be used with .using(alias).
    Raises ValueError when the tenant has no mongo_uri configured.

    Alias format: "tenant_{tenant_id}_{db_name}"
    """
    try:
        import mongoengine
        uri = tenant.mongo_uri
        if not uri:
            raise ValueError(
                f"Tenant '{tenant.name}' has no mongo_uri configured in Supabase."
            )
        alias = f"tenant_{tenant.id}_{db_name}"
        if alias not in mongoengine.connection._get_connection_settings():
            mongoengine.connect(db=db_name, host=uri, alias=alias)
            source = "tenant-specific" if tenant.mongo_uri else "global fallback"
            logger.info(f"Registered MongoEngine alias '{alias}' for tenant '{tenant.name}' using {source} URI")
        return alias
    except Exception as e:
        logger.warning(f"ensure_mongo_connection_for_tenant failed for '{tenant.name}': {e}")
        return None
