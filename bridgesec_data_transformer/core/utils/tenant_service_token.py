"""
Service-app OAuth (Client Credentials) token acquisition per tenant.

Mirrors core/utils/service_token.py but accepts a Tenant object
instead of reading from global settings.
"""
import base64
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

import requests
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from jose import jwt

logger = logging.getLogger(__name__)


def _load_private_key(raw_key: str):
    """Load private key from JWK JSON or PEM string."""
    try:
        return json.loads(raw_key)
    except (json.JSONDecodeError, ValueError):
        return raw_key.replace('\\n', '\n')


def _get_token_endpoint(tenant) -> str:
    """
    Derive the correct Okta token endpoint for this tenant.

    Mirrors OktaCallbackView logic: use okta_issuer to detect custom auth server
    (e.g. /oauth2/default) vs org auth server.  Falls back to okta_domain when
    okta_issuer is not stored.

    Also guards against okta_domain already containing the https:// scheme so
    we never produce a double-scheme URL like https://https://...
    """
    issuer = (getattr(tenant, 'okta_issuer', None) or '').rstrip('/')

    if issuer:
        if '/oauth2/' in issuer:
            # Custom authorization server: https://domain.okta.com/oauth2/default
            return f"{issuer}/v1/token"
        else:
            # Org authorization server: https://domain.okta.com
            return f"{issuer}/oauth2/v1/token"

    # Fallback: derive from okta_domain (okta_issuer not stored on this tenant)
    domain = (tenant.okta_domain or '').rstrip('/')
    if not domain.startswith('http'):
        domain = f"https://{domain}"
    return f"{domain}/oauth2/v1/token"


def create_client_assertion_for_tenant(tenant, token_endpoint: str) -> str:
    """
    Create a signed RS256 JWT assertion for the given tenant's service app.

    token_endpoint is passed in (not recomputed here) so the 'aud' claim
    exactly matches the URL the caller will POST to — Okta rejects the
    assertion if they differ by even a trailing slash.
    """
    client_id   = tenant.service_client_id
    private_key = _load_private_key(tenant.service_private_key)
    now = datetime.utcnow()

    payload = {
        "iss": client_id,
        "sub": client_id,
        "aud": token_endpoint,
        "iat": now,
        "exp": now + timedelta(hours=1),
        "jti": str(uuid.uuid4()),
    }

    logger.debug(f"Creating tenant client assertion for client_id={client_id}, aud={token_endpoint}")
    return jwt.encode(payload, private_key, algorithm="RS256")


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def _generate_dpop_proof(http_method: str, http_url: str, nonce: str | None = None) -> str:
    """
    Build a DPoP proof JWT for a single request per RFC 9449.

    Generates a fresh ephemeral EC P-256 key pair each call so the proof
    is single-use (Okta rejects replays).  The public key is embedded in
    the JWT header as a JWK so Okta can verify the signature without any
    pre-registered key material.

    When the server requires a nonce (use_dpop_nonce flow), pass the value
    from the DPoP-Nonce response header as `nonce`.
    """
    private_key = ec.generate_private_key(ec.SECP256R1())
    pub_numbers = private_key.public_key().public_numbers()

    # P-256 coordinates must be exactly 32 bytes (zero-padded)
    public_jwk = {
        "kty": "EC",
        "crv": "P-256",
        "x": _base64url_encode(pub_numbers.x.to_bytes(32, "big")),
        "y": _base64url_encode(pub_numbers.y.to_bytes(32, "big")),
    }

    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    payload = {
        "jti": str(uuid.uuid4()),
        "htm": http_method.upper(),
        "htu": http_url,
        "iat": int(datetime.now(timezone.utc).timestamp()),
    }
    if nonce:
        payload["nonce"] = nonce

    # python-jose merges `headers` into the default header dict;
    # "typ" here overrides the default "JWT" value.
    return jwt.encode(
        payload,
        pem,
        algorithm="ES256",
        headers={"typ": "dpop+jwt", "jwk": public_jwk},
    )


def get_service_access_token_for_tenant(tenant) -> tuple:
    """
    Obtain an Okta access token for the given tenant using Client Credentials flow.

    Args:
        tenant: SupabaseTenant with service_client_id, service_private_key,
                service_scopes, and either okta_issuer or okta_domain populated.

    Returns:
        (access_token: str, granted_scopes: list[str])

    Raises:
        ValueError: If token acquisition fails or required fields are missing.
    """
    if not tenant.service_client_id:
        raise ValueError(f"Tenant '{tenant.name}' has no service_client_id configured")
    if not tenant.service_private_key:
        raise ValueError(f"Tenant '{tenant.name}' has no service_private_key configured")
    if not tenant.service_scopes:
        raise ValueError(f"Tenant '{tenant.name}' has no service_scopes configured")

    # Single source of truth for the token endpoint — reused for both the
    # JWT assertion 'aud' claim and the actual POST request.
    token_endpoint = _get_token_endpoint(tenant)

    logger.info(f"Requesting service access token for tenant '{tenant.name}' from {token_endpoint}")

    base_headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }

    # RFC 9449 §8: servers may require a server-provided nonce.
    # First attempt is sent without a nonce; if the server responds with
    # use_dpop_nonce we extract the DPoP-Nonce header and retry once.
    #
    # Both client_assertion and DPoP proof are regenerated on each attempt:
    # client_assertion carries a jti that Okta marks as used after the first
    # request, so reusing it on the retry triggers "already been used".
    nonce = None
    for attempt in range(2):
        try:
            client_assertion = create_client_assertion_for_tenant(tenant, token_endpoint)
            dpop_proof = _generate_dpop_proof("POST", token_endpoint, nonce=nonce)
        except Exception as e:
            raise ValueError(f"Failed to build DPoP credentials for tenant '{tenant.name}': {e}") from e

        try:
            response = requests.post(
                token_endpoint,
                data={
                    "grant_type": "client_credentials",
                    "scope": tenant.service_scopes,
                    "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
                    "client_assertion": client_assertion,
                },
                headers={**base_headers, "DPoP": dpop_proof},
                timeout=30,
            )
        except requests.RequestException as e:
            raise ValueError(f"Token endpoint request failed for tenant '{tenant.name}': {e}") from e

        # Server requires a nonce — grab it from the response header and retry.
        if (
            response.status_code == 400
            and attempt == 0
            and "use_dpop_nonce" in response.text
        ):
            nonce = response.headers.get("DPoP-Nonce")
            if nonce:
                logger.debug(
                    f"Okta requires DPoP nonce for tenant '{tenant.name}', retrying with nonce."
                )
                continue

        break  # success or unrecoverable error

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
