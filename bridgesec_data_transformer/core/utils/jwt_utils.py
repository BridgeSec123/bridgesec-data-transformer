import logging
from datetime import datetime, timedelta
from functools import lru_cache

import requests
from django.conf import settings
from jose import JWTError, jwt

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_cached_jwks():
    """
    Fetch and cache Okta's JWKS for token validation.
    """
    jwks_url = f"{settings.OKTA_ISSUER}/v1/keys"
    response = requests.get(jwks_url)
    return response.json()

def generate_jwt_token(user, expiry_hours: int = 24, login_tenant_id: str = None):
    roles = getattr(user, "roles", None) or []
    # Use login_tenant_id (the tenant they logged in through) when provided.
    # Falls back to user.tenant_id for backwards-compatible callers.
    # Super admin has user.tenant_id=None, so login_tenant_id is essential for them.
    tenant_id = login_tenant_id or (str(user.tenant_id) if getattr(user, "tenant_id", None) else None)

    # Multi-tenancy: roles are stored per (email, tenant_id) row in users.
    # Fetch the tenant-specific row to get the correct roles for this session.
    # super_admin is a global role and is preserved as-is.
    if getattr(settings, "MULTI_TENANCY_ENABLED", False) and tenant_id and "super_admin" not in roles:
        try:
            from core.utils.supabase_user import SupabaseUser
            tenant_user = SupabaseUser.get_by_email(user.email, tenant_id=str(tenant_id))
            if tenant_user and tenant_user.roles:
                roles = tenant_user.roles
        except Exception as e:
            logger.warning(f"Per-tenant role lookup failed for user={user.email} tenant={tenant_id}: {e}")

    payload = {
        "user_id":   str(user.id),
        "email":     user.email,
        "roles":     roles,
        "tenant_id": tenant_id,
        "exp":       datetime.utcnow() + timedelta(hours=expiry_hours),
        "iat":       datetime.utcnow(),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def get_user_from_request(request):
    """
    Extract user info from JWT token (Okta or custom) and fetch username/email from database.
    Returns username or email, or 'Unknown' if extraction fails.

    Supports both:
    1. Okta Access Tokens (RS256)
    2. Custom JWT tokens (HS256) - for username/password login
    """
    try:
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            logger.warning("No Bearer token found in request")
            return "Unknown"

        token = auth_header.split(' ')[1]
        decoded = None
        email = None
        user_id = None

        # Determine token algorithm without verification
        try:
            unverified_header = jwt.get_unverified_header(token)
        except Exception as e:
            logger.warning(f"Could not read token header: {str(e)}")
            return "Unknown"

        token_alg = unverified_header.get("alg", "")
        kid = unverified_header.get("kid")

        # Try decoding as Okta token (RS256)
        if token_alg == "RS256" and kid:
            try:
                jwks = get_cached_jwks()
                key = next((k for k in jwks["keys"] if k["kid"] == kid), None)

                # kid not in cached JWKS — Okta may have rotated keys, refresh and retry
                if not key:
                    logger.info(f"kid '{kid}' not found in cached JWKS, refreshing...")
                    get_cached_jwks.cache_clear()
                    jwks = get_cached_jwks()
                    key = next((k for k in jwks["keys"] if k["kid"] == kid), None)

                if key:
                    decoded = jwt.decode(
                        token,
                        key,
                        algorithms=["RS256"],
                        audience=settings.OKTA_ISSUER,
                        issuer=settings.OKTA_ISSUER,
                    )
                    email = decoded.get("sub") or decoded.get("email")
                    logger.info(f"Decoded Okta token for user: {email}")
                else:
                    logger.warning(f"kid '{kid}' not found in JWKS even after refresh")
            except Exception as okta_error:
                logger.debug(f"Okta RS256 decode failed: {str(okta_error)}")

        # SECURITY: do NOT fall back to unverified claims. If RS256 verification
        # failed (bad signature, expired, wrong issuer/audience), the token's
        # identity cannot be trusted — leave email as "Unknown".
        if not decoded and token_alg == "RS256":
            logger.warning("Okta RS256 token failed verification; refusing to read unverified claims")

        # Try custom HS256 JWT (username/password login)
        if not decoded and token_alg != "RS256":
            try:
                decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                user_id = decoded.get('user_id')
                email = decoded.get('email')
                logger.info(f"Decoded custom JWT for user_id: {user_id}",extra={"operation":"Get User From Request"})
            except Exception as jwt_error:
                logger.warning(f"Failed to decode both Okta and custom JWT: {str(jwt_error)}",extra={"operation":"Get User From Request"})
                return "Unknown"

        # Fetch user from the configured backend (Supabase or MongoDB)
        try:
            from core.authentication import _get_user_backend
            UserBackend = _get_user_backend()

            # Try to find user by email first (works for both token types)
            if email:
                user = UserBackend.get_by_email(email)
                if user:
                    user_identifier = user.username or user.email
                    logger.info(f"Found user by email: {user_identifier}", extra={"operation": "Get User From Request"})
                    return str(user_identifier)

            # Fallback to user_id for custom JWT tokens
            if user_id:
                user = UserBackend.get_by_id(str(user_id))
                if user:
                    user_identifier = user.username or user.email
                    logger.info(f"Found user by ID: {user_identifier}", extra={"operation": "Get User From Request"})
                    return str(user_identifier)

            logger.warning("No email or user_id found in token", extra={"operation": "Get User From Request"})
            return "Unknown"

        except Exception as db_error:
            logger.warning(f"Database error fetching user: {str(db_error)}", extra={"operation": "Get User From Request"})
            return email or user_id or "Unknown"

    except Exception as e:
        logger.warning(f"Failed to extract user from token: {str(e)}",extra={"operation":"Get User From Request"})
        return "Unknown"