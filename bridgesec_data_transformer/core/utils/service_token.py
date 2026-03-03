import json
import logging
import uuid
from datetime import datetime, timedelta

import requests
from django.conf import settings
from jose import jwt

logger = logging.getLogger(__name__)


def _load_private_key(raw_key: str):
    """
    Load the private key from either JWK JSON format or PEM format.

    Okta's Admin Console exports keys as JWK (JSON). Both formats are supported:
    - JWK JSON  : {"kty":"RSA","d":"...","n":"...","e":"AQAB", ...}
    - PEM string: "-----BEGIN RSA PRIVATE KEY-----\\n..."

    Returns:
        dict | str: JWK dict (for JSON keys) or PEM string (for PEM keys)
    """
    try:
        key = json.loads(raw_key)
        logger.debug("Private key loaded as JWK JSON format")
        return key
    except (json.JSONDecodeError, ValueError):
        # Not JSON — treat as PEM, fix newline encoding from env var
        pem_key = raw_key.replace('\\n', '\n')
        logger.debug("Private key loaded as PEM format")
        return pem_key


def create_client_assertion():
    """
    Create a signed JWT assertion for the Client Credentials grant.

    The JWT is signed with the service app's RSA private key and sent to Okta's
    token endpoint in exchange for an access token.

    Supports both JWK JSON (exported from Okta Admin Console) and PEM key formats.

    Claims:
        iss: Service app client ID
        sub: Service app client ID
        aud: Okta token endpoint URL
        iat: Issued at (now)
        exp: Expiry (1 hour from now)
        jti: Unique token ID (prevents replay attacks)

    Returns:
        str: Signed RS256 JWT assertion
    """
    client_id = settings.OKTA_SERVICE_CLIENT_ID
    private_key = _load_private_key(settings.OKTA_SERVICE_PRIVATE_KEY)

    # Service apps use the Okta org authorization server endpoint: /oauth2/v1/token
    # OKTA_API_URL is the base domain e.g. https://coolbeans.oktapreview.com
    token_endpoint = f"{settings.OKTA_API_URL}/oauth2/v1/token"
    now = datetime.utcnow()

    payload = {
        "iss": client_id,
        "sub": client_id,
        "aud": token_endpoint,
        "iat": now,
        "exp": now + timedelta(hours=1),
        "jti": str(uuid.uuid4()),
    }

    logger.debug(f"Creating client assertion for client_id={client_id}, aud={token_endpoint}")

    return jwt.encode(payload, private_key, algorithm="RS256")


def get_service_access_token():
    """
    Obtain an Okta access token using the Client Credentials grant flow
    with a private key JWT assertion.

    This is used by scheduled Celery tasks where no user session is available.
    The service app must have the required scopes pre-granted in the Okta Admin Console
    (Applications > Your Service App > Okta API Scopes).

    Returns:
        tuple: (access_token: str, granted_scopes: list[str])

    Raises:
        ValueError: If token request fails or required settings are missing
    """
    client_id = settings.OKTA_SERVICE_CLIENT_ID
    scopes = settings.OKTA_SERVICE_SCOPES

    if not client_id:
        raise ValueError("OKTA_SERVICE_CLIENT_ID is not configured in settings")

    if not settings.OKTA_SERVICE_PRIVATE_KEY:
        raise ValueError("OKTA_SERVICE_PRIVATE_KEY is not configured in settings")

    if not scopes:
        raise ValueError("OKTA_SERVICE_SCOPES is not configured in settings")

    token_endpoint = f"{settings.OKTA_API_URL}/oauth2/v1/token"

    try:
        client_assertion = create_client_assertion()
    except Exception as e:
        logger.exception(f"Failed to create client assertion JWT: {e}")
        raise ValueError(f"Failed to sign client assertion: {e}") from e

    logger.info(f"Requesting service access token from {token_endpoint}")

    try:
        response = requests.post(
            token_endpoint,
            data={
                "grant_type": "client_credentials",
                "scope": scopes,
                "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
                "client_assertion": client_assertion,
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            timeout=30,
        )
    except requests.RequestException as e:
        logger.exception(f"HTTP request to Okta token endpoint failed: {e}")
        raise ValueError(f"Token endpoint request failed: {e}") from e

    if not response.ok:
        logger.error(
            f"Okta token endpoint returned {response.status_code}: {response.text}"
        )
        raise ValueError(
            f"Failed to obtain service access token: HTTP {response.status_code} — {response.text}"
        )

    data = response.json()
    access_token = data.get("access_token")

    if not access_token:
        logger.error(f"No access_token in Okta response: {data}")
        raise ValueError(f"Okta returned no access_token. Response: {data}")

    # Parse granted scopes from response (space-separated string)
    scope_string = data.get("scope", "")
    granted_scopes = scope_string.split() if scope_string else []

    logger.info(
        f"Service access token obtained successfully. "
        f"Expires in: {data.get('expires_in', 'unknown')}s. "
        f"Scopes granted: {len(granted_scopes)}"
    )
    logger.debug(f"Granted scopes: {granted_scopes}")

    return access_token, granted_scopes
