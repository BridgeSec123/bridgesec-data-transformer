import requests
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from jose import jwt
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


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
            user = UserBackend.get_by_id(user_id)
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
                    _tenant = get_tenant_by_id(request._tenant_id)
                    if _tenant:
                        request._tenant       = _tenant
                        request._mongo_client = get_mongo_client_for_tenant(_tenant)
                        request._db_prefix    = _tenant.mongo_db_prefix
                        request._mongo_uri    = _tenant.mongo_uri
                except Exception as _e:
                    logger.warning(f"Tenant resource init failed for tenant_id={request._tenant_id}: {_e}")

            # Store the resolved tenant object in ContextVar so log records carry tenant_id
            try:
                from core.utils.tenant_utils import set_current_tenant
                set_current_tenant(getattr(request, '_tenant', None))
            except Exception:
                pass

            return (user, None)
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
        Also stores the token in session for subsequent Okta API calls.
        """
        try:
            # Normalize OKTA_ISSUER - remove trailing slash if present
            issuer_base = settings.OKTA_ISSUER.rstrip('/')

            # Build JWKS URL - handle both org and custom auth servers
            if '/oauth2/' in issuer_base:
                # Custom authorization server (e.g., /oauth2/default)
                jwks_url = f"{issuer_base}/v1/keys"
            else:
                # Org authorization server
                jwks_url = f"{issuer_base}/oauth2/v1/keys"

            # Get Okta JWKS for token verification
            jwks_response = requests.get(jwks_url)
            jwks = jwks_response.json()

            # Get token header to find the key
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")

            # Find matching key
            key = next((k for k in jwks.get("keys", []) if k["kid"] == kid), None)
            if not key:
                logger.warning("No matching key found for Okta token")
                return None

            # Verify the token. Audience AND issuer are now enforced (fail-closed).
            # OKTA_AUDIENCE must match the `aud` your Okta authorization server issues
            # (default auth server -> "api://default"; org server -> the issuer URL).
            expected_audience = getattr(settings, "OKTA_AUDIENCE", "api://default")
            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=expected_audience,
                issuer=settings.OKTA_ISSUER,
                options={"verify_aud": True, "verify_iss": True},
            )

            # Get user email from token
            email = payload.get("sub") or payload.get("email")
            if not email:
                logger.warning("No email/sub found in Okta token")
                return None

            # Find or create user (Supabase or MongoDB depending on config)
            UserBackend = _get_user_backend()
            user = UserBackend.get_by_email(email)
            if not user:
                user = UserBackend.create_or_update(email=email, username=email, roles=["user"])
                logger.info(f"Created new user from Okta token: {email}")

            # Store Okta access token in session for API calls
            if hasattr(request, 'session'):
                request.session['okta_access_token'] = token
                request.session['okta_granted_scopes'] = payload.get('scp', [])
                request.session.save()
                logger.info(f"Stored Okta access token in session for user: {email}")

            # Mirror the same attribute set by the HS256 path so downstream
            # code (e.g. UserManagementViewSet) can always read request._tenant_id.
            request._tenant_id = str(user.tenant_id) if getattr(user, "tenant_id", None) else None

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
