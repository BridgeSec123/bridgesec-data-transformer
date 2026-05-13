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
            if not hasattr(user, 'roles'):
                user.roles = payload.get('roles', ['user'])
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

            # Verify the token
            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience="api://default",  # Okta default audience
                options={"verify_aud": False}  # Skip audience verification for flexibility
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
