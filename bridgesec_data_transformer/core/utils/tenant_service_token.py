"""
Service-app OAuth (Client Credentials) token acquisition per tenant.

Mirrors core/utils/service_token.py but accepts a Tenant object
instead of reading from global settings.
"""
import json
import logging
import uuid
from datetime import datetime, timedelta

import requests
from jose import jwt

logger = logging.getLogger(__name__)


def _load_private_key(raw_key: str):
    """Load private key from JWK JSON or PEM string."""
    try:
        return json.loads(raw_key)
    except (json.JSONDecodeError, ValueError):
        return raw_key.replace('\\n', '\n')


def create_client_assertion_for_tenant(tenant) -> str:
    """
    Create a signed RS256 JWT assertion for the given tenant's service app.
    """
    client_id = tenant.service_client_id
    private_key = _load_private_key(tenant.service_private_key)

    # Derive token endpoint from okta_domain
    token_endpoint = f"https://{tenant.okta_domain}/oauth2/v1/token"
    now = datetime.utcnow()

    payload = {
        "iss": client_id,
        "sub": client_id,
        "aud": token_endpoint,
        "iat": now,
        "exp": now + timedelta(hours=1),
        "jti": str(uuid.uuid4()),
    }

    logger.debug(f"Creating tenant client assertion for client_id={client_id}")
    return jwt.encode(payload, private_key, algorithm="RS256")


def get_service_access_token_for_tenant(tenant) -> tuple:
    """
    Obtain an Okta access token for the given tenant using Client Credentials flow.

    Args:
        tenant: Tenant document with service_client_id, service_private_key, service_scopes

    Returns:
        (access_token: str, granted_scopes: list[str])

    Raises:
        ValueError: If token acquisition fails or required fields are missing
    """
    if not tenant.service_client_id:
        raise ValueError(f"Tenant '{tenant.name}' has no service_client_id configured")
    if not tenant.service_private_key:
        raise ValueError(f"Tenant '{tenant.name}' has no service_private_key configured")
    if not tenant.service_scopes:
        raise ValueError(f"Tenant '{tenant.name}' has no service_scopes configured")

    token_endpoint = f"https://{tenant.okta_domain}/oauth2/v1/token"

    try:
        client_assertion = create_client_assertion_for_tenant(tenant)
    except Exception as e:
        raise ValueError(f"Failed to sign client assertion for tenant '{tenant.name}': {e}") from e

    logger.info(f"Requesting service access token for tenant '{tenant.name}' from {token_endpoint}")

    try:
        response = requests.post(
            token_endpoint,
            data={
                "grant_type": "client_credentials",
                "scope": tenant.service_scopes,
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
        raise ValueError(f"Token endpoint request failed for tenant '{tenant.name}': {e}") from e

    if not response.ok:
        raise ValueError(
            f"Failed to obtain service access token for tenant '{tenant.name}': "
            f"HTTP {response.status_code} — {response.text}"
        )

    data = response.json()
    access_token = data.get("access_token")
    if not access_token:
        raise ValueError(f"Okta returned no access_token for tenant '{tenant.name}'. Response: {data}")

    scope_string = data.get("scope", "")
    granted_scopes = scope_string.split() if scope_string else []

    logger.info(
        f"Service access token obtained for tenant '{tenant.name}'. "
        f"Expires in: {data.get('expires_in', 'unknown')}s. "
        f"Scopes: {len(granted_scopes)}"
    )

    return access_token, granted_scopes
