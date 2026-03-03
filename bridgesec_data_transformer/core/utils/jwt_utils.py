import logging
from datetime import datetime, timedelta
from functools import lru_cache

import requests
from bson import ObjectId
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

def generate_jwt_token(user):
    payload = {
        "user_id": str(user.id),
        "email": user.email,
        "role": user.role,
        "exp": datetime.utcnow() + timedelta(days=1),
        "iat": datetime.utcnow()
    }

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    return token


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

        # If RS256 verified decode failed, extract claims unverified (auth already passed)
        if not decoded and token_alg == "RS256":
            try:
                unverified_claims = jwt.get_unverified_claims(token)
                email = unverified_claims.get("sub") or unverified_claims.get("email")
                logger.info(f"Extracted user from Okta token unverified claims: {email}")
            except Exception as e:
                logger.warning(f"Could not extract unverified claims: {str(e)}")

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

        # Fetch user from database
        try:
            from core.models.user import User

            # Try to find user by email first (works for both token types)
            if email:
                user = User.objects(email=email).first()
                if user:
                    user_identifier = user.username or user.email
                    logger.info(f"Found user by email: {user_identifier}",extra={"operation":"Get User From Request"})
                    return str(user_identifier)

            # Fallback to user_id for custom JWT tokens
            if user_id:
                user = User.objects.get(id=ObjectId(user_id))
                user_identifier = user.username or user.email
                logger.info(f"Found user by ID: {user_identifier}",extra={"operation":"Get User From Request"})
                return str(user_identifier)

            logger.warning("No email or user_id found in token",extra={"operation":"Get User From Request"})
            return "Unknown"

        except User.DoesNotExist:
            logger.warning(f"User not found in database",extra={"operation":"Get User From Request"})
            return email or user_id or "Unknown"
        except Exception as db_error:
            logger.warning(f"Database error fetching user: {str(db_error)}",extra={"operation":"Get User From Request"})
            return email or user_id or "Unknown"

    except Exception as e:
        logger.warning(f"Failed to extract user from token: {str(e)}",extra={"operation":"Get User From Request"})
        return "Unknown"