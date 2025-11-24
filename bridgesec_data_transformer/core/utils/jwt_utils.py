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

        # Try decoding as Okta token first (RS256)
        try:
            jwks = get_cached_jwks()
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")

            if kid:
                key = next((k for k in jwks["keys"] if k["kid"] == kid), None)
                if key:
                    decoded = jwt.decode(
                        token,
                        key,
                        algorithms=["RS256"],
                        audience="api://default",
                        issuer=settings.OKTA_ISSUER,
                    )
                    # Okta token: extract email from 'sub' or 'email' claim
                    email = decoded.get("sub") or decoded.get("email")
                    logger.info(f"Decoded Okta token for user: {email}")
        except Exception as okta_error:
            logger.debug(f"Not an Okta token, trying custom JWT: {str(okta_error)}")

        # If Okta decode failed, try custom JWT (HS256)
        if not decoded:
            try:
                decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                user_id = decoded.get('user_id')
                email = decoded.get('email')
                logger.info(f"Decoded custom JWT for user_id: {user_id}")
            except Exception as jwt_error:
                logger.warning(f"Failed to decode both Okta and custom JWT: {str(jwt_error)}")
                return "Unknown"

        # Fetch user from database
        try:
            from core.models.user import User

            # Try to find user by email first (works for both token types)
            if email:
                user = User.objects(email=email).first()
                if user:
                    user_identifier = user.username or user.email
                    logger.info(f"Found user by email: {user_identifier}")
                    return str(user_identifier)

            # Fallback to user_id for custom JWT tokens
            if user_id:
                user = User.objects.get(id=ObjectId(user_id))
                user_identifier = user.username or user.email
                logger.info(f"Found user by ID: {user_identifier}")
                return str(user_identifier)

            logger.warning("No email or user_id found in token")
            return "Unknown"

        except User.DoesNotExist:
            logger.warning(f"User not found in database")
            return email or user_id or "Unknown"
        except Exception as db_error:
            logger.warning(f"Database error fetching user: {str(db_error)}")
            return email or user_id or "Unknown"

    except Exception as e:
        logger.warning(f"Failed to extract user from token: {str(e)}")
        return "Unknown"