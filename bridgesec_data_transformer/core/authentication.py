import time
import requests
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from jose import jwt
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def _log_latency(label, start_time, request=None):
    """Log how long a single auth sub-step took, so slow steps show up in the
    logs as [AUTH_LATENCY] lines greppable independently of total request time."""
    duration_ms = int((time.time() - start_time) * 1000)
    logger.info(
        f"[AUTH_LATENCY] {label}: {duration_ms}ms",
        extra={
            'component': 'auth_timing',
            'auth_step': label,
            'duration_ms': duration_ms,
            'request_id': getattr(request, 'request_id', 'N/A') if request else 'N/A',
        }
    )
    return duration_ms


def _get_user_backend():
    """Always returns the Supabase user backend. MongoDB is snapshot-only."""
    from core.utils.supabase_user import SupabaseUser
    return SupabaseUser


class CustomJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')

        if not auth_header or not auth_header.startswith('Bearer'):
            return None

        parts = auth_header.split(' ', 1)
        if len(parts) < 2 or not parts[1].strip():
            return None
        token = parts[1].strip()

        # First, try to decode as internal JWT token (HS256)
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            user_id = payload.get('user_id')
            UserBackend = _get_user_backend()

            _t0 = time.time()
            user = UserBackend.get_by_id(user_id)
            _log_latency("supabase_get_user_by_id", _t0, request)

            if not user:
                raise Exception("User not found")
            # Attach tenant_id and roles from JWT to the request
            request._tenant_id = payload.get('tenant_id')
            # Under multi-tenancy the JWT roles claim is scoped to the active tenant
            # (see generate_jwt_token) and is authoritative — it overrides the global
            # users.roles loaded onto the SupabaseUser. In single-tenant mode the claim
            # equals the global roles, so only fill in when the user has none.
            jwt_roles = payload.get('roles')
            if getattr(settings, 'MULTI_TENANCY_ENABLED', False) and jwt_roles is not None:
                user.roles = jwt_roles
            elif not getattr(user, 'roles', None):
                user.roles = jwt_roles or ['user']

            # Eagerly resolve tenant resources so every downstream code path
            # reads request._mongo_client / _db_prefix instead of falling back
            # to the global settings.MONGO_CLIENT (which is the default tenant).
            if getattr(settings, 'MULTI_TENANCY_ENABLED', False) and request._tenant_id:
                try:
                    from core.utils.tenant_utils import get_tenant_by_id, get_mongo_client_for_tenant

                    _t0 = time.time()
                    _tenant = get_tenant_by_id(request._tenant_id)
                    _log_latency("supabase_get_tenant_by_id", _t0, request)

                    if _tenant:
                        request._tenant       = _tenant

                        _t0 = time.time()
                        request._mongo_client = get_mongo_client_for_tenant(_tenant)
                        _log_latency("get_mongo_client_for_tenant", _t0, request)

                        request._db_prefix    = _tenant.mongo_db_prefix
                        request._mongo_uri    = _tenant.mongo_uri
                except Exception as _e:
                    logger.warning(f"Tenant resource init failed for tenant_id={request._tenant_id}: {_e}")

            # Store the resolved tenant object in ContextVar so log records carry tenant_id
            try:
                from core.utils.tenant_utils import set_current_tenant, set_current_user
                set_current_tenant(getattr(request, '_tenant', None))
                set_current_user(getattr(user, 'email', None))
            except Exception:
                pass

            return (user, None)
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token has expired')
        except Exception:
            pass  # Not an internal token, try Okta token

        # Try to validate as Okta access token
        try:
            user = self._authenticate_okta_token(request, token)
            if user:
                return (user, None)
        except Exception as e:
            logger.warning(f"Okta token authentication failed: {e}")

        raise AuthenticationFailed('Invalid or expired token')

    def _authenticate_okta_token(self, request, token):
        """
        Validate Okta access token and return user.

        In multi-tenant mode the issuer (`iss`) claim is read from the unverified
        token, the matching tenant is looked up from Supabase, and that tenant's
        `okta_issuer` / `okta_audience` are used for validation — no global .env
        values needed. Falls back to settings.OKTA_ISSUER / OKTA_AUDIENCE when
        no tenant matches (single-tenant or unknown issuer).
        """
        try:
            # Read iss from unverified claims to identify which tenant issued this token.
            unverified_claims = jwt.get_unverified_claims(token)
            token_issuer = (unverified_claims.get("iss") or "").rstrip("/")

            # Resolve per-tenant Okta config via issuer URL.
            tenant = None
            if token_issuer:
                from core.utils.supabase_tenant import SupabaseTenant
                tenant = SupabaseTenant.get_by_okta_issuer(token_issuer)

            # Per-tenant values take priority; fall back to global settings.
            issuer_base = (
                (tenant.okta_issuer if tenant else None) or settings.OKTA_ISSUER
            ).rstrip("/")
            # okta_audience == okta_issuer for Okta service tokens.
            expected_audience = issuer_base

            # Build JWKS URL — handle both org and custom auth servers.
            if "/oauth2/" in issuer_base:
                jwks_url = f"{issuer_base}/v1/keys"
            else:
                jwks_url = f"{issuer_base}/oauth2/v1/keys"

            _t0 = time.time()
            jwks_response = requests.get(jwks_url)
            jwks = jwks_response.json()
            _log_latency("okta_jwks_fetch", _t0, request)

            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            key = next((k for k in jwks.get("keys", []) if k["kid"] == kid), None)
            if not key:
                logger.warning(
                    f"No matching key found for kid={kid} issuer={issuer_base}",
                    extra={"component": "auth", "tenant_id": str(tenant.id) if tenant else None}
                )
                return None

            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=expected_audience,
                issuer=issuer_base,
                options={"verify_aud": True, "verify_iss": True},
            )

            email = payload.get("sub") or payload.get("email")
            if not email:
                logger.warning("No email/sub found in Okta token")
                return None

            UserBackend = _get_user_backend()

            _t0 = time.time()
            user = UserBackend.get_by_email(email)
            _log_latency("supabase_get_user_by_email", _t0, request)

            if not user:
                user = UserBackend.create_or_update(email=email, username=email, roles=["user"])
                logger.info(f"Created new user from Okta token: {email}")

            if hasattr(request, 'session'):
                request.session['okta_access_token'] = token
                request.session['okta_granted_scopes'] = payload.get('scp', [])
                request.session.save()
                logger.info(f"Stored Okta access token in session for user: {email}")

            request._tenant_id = str(user.tenant_id) if getattr(user, "tenant_id", None) else None

            # Guard: the tenant resolved from the unverified `iss` claim must match
            # the tenant on the Supabase user record. Without this check, an attacker
            # controlling their own Okta org could issue a token with sub=victim@email
            # and get authenticated as the victim's tenant.
            if tenant and getattr(user, 'tenant_id', None):
                if str(user.tenant_id) != str(tenant.id):
                    logger.warning(
                        f"Issuer/user tenant mismatch: iss tenant={tenant.id}, "
                        f"user.tenant_id={user.tenant_id} — rejecting token"
                    )
                    return None

            # Attach the resolved tenant so downstream code avoids a second Supabase call.
            if tenant and not getattr(request, '_tenant', None):
                request._tenant = tenant

            # Store the authenticated user's email in ContextVar so log records carry it
            try:
                from core.utils.tenant_utils import set_current_user
                set_current_user(email)
            except Exception:
                pass

            return user

        except jwt.ExpiredSignatureError:
            logger.warning("Okta token has expired")
            return None
        except jwt.JWTClaimsError as e:
            logger.warning(f"Okta token claims error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error validating Okta token: {e}")
            return None
