"""
Service-app OAuth (Client Credentials) token acquisition per tenant.

Mirrors core/utils/service_token.py but accepts a Tenant object
instead of reading from global settings.
"""
import base64
import hashlib
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit, urlunsplit

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
        # Handle double-encoded first (\\n → \n), then single-encoded (\n literal → newline).
        # Order matters: double must run before single or the result still contains a stray 'n'.
        key = raw_key.replace('\\\\n', '\n').replace('\\n', '\n')
        return key.strip().strip('"')


def _get_token_endpoint(tenant) -> str:
    """
    Derive the Okta org-level token endpoint for this tenant's service app.

    Service app tokens used for Okta management API calls (e.g. via the Terraform
    provider) MUST be issued by the org authorization server — not by a custom or
    default auth server. Custom auth server tokens (iss containing /oauth2/) are
    rejected with 400 by /api/v1/apps/* and similar management endpoints regardless
    of which scopes are granted.

    okta_issuer stores the OIDC issuer (often /oauth2/default) which is correct for
    user login but wrong for management API tokens. We always derive the org-level
    endpoint from okta_domain, falling back to stripping the /oauth2/... path from
    okta_issuer if okta_domain is absent.

    Guards against okta_domain already containing the https:// scheme to avoid
    double-scheme URLs like https://https://...
    """
    # Prefer okta_domain — it is the bare org hostname, always org-level.
    domain = (getattr(tenant, 'okta_domain', None) or '').rstrip('/')
    if domain:
        if not domain.startswith('http'):
            domain = f"https://{domain}"
        return f"{domain}/oauth2/v1/token"

    # Fallback: strip the /oauth2/... path from okta_issuer to reach the org root.
    issuer = (getattr(tenant, 'okta_issuer', None) or '').rstrip('/')
    if issuer:
        if '/oauth2/' in issuer:
            # e.g. https://domain.okta.com/oauth2/default → https://domain.okta.com
            org_root = issuer.split('/oauth2/')[0]
        else:
            org_root = issuer
        return f"{org_root}/oauth2/v1/token"

    raise ValueError(f"Tenant '{getattr(tenant, 'name', '?')}' has neither okta_domain nor okta_issuer configured")


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


def generate_dpop_proof(
    http_method: str,
    http_url: str,
    nonce: str | None = None,
    private_key=None,
    access_token: str | None = None,
) -> str:
    """
    Build a DPoP proof JWT for a single request per RFC 9449.

    The proof is single-use (unique jti + iat), so a fresh JWT is built every
    call. When `private_key` is None a fresh ephemeral EC P-256 key pair is
    generated — use this only for the token-acquisition request. For all
    subsequent API calls pass the same key that was used during token
    acquisition; the access token is cryptographically bound (cnf.jkt) to that
    key and Okta rejects proofs signed by a different key.

    `access_token` must be supplied for resource server requests (RFC 9449 §4.2).
    The `ath` claim (base64url SHA-256 of the token) is required by Okta for
    all API calls; omit it only for the token endpoint request itself.

    When the server requires a nonce (use_dpop_nonce flow), pass the value
    from the DPoP-Nonce response header as `nonce`.
    """
    if private_key is None:
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

    # RFC 9449 §4.2: htu is the HTTP target URI without the query or fragment —
    # Okta rejects the proof outright if either is present (confirmed live: a
    # bare "/api/v1/users" proof is accepted, the same request with "?limit=1"
    # comes back 400 invalid_dpop_proof).
    split_url = urlsplit(http_url)
    htu = urlunsplit((split_url.scheme, split_url.netloc, split_url.path, "", ""))

    payload = {
        "jti": str(uuid.uuid4()),
        "htm": http_method.upper(),
        "htu": htu,
        "iat": int(datetime.now(timezone.utc).timestamp()),
    }
    if nonce:
        payload["nonce"] = nonce
    if access_token:
        # RFC 9449 §4.2: ath = base64url(SHA-256(ASCII(access_token)))
        payload["ath"] = _base64url_encode(
            hashlib.sha256(access_token.encode("ascii")).digest()
        )

    # python-jose merges `headers` into the default header dict;
    # "typ" here overrides the default "JWT" value.
    return jwt.encode(
        payload,
        pem,
        algorithm="ES256",
        headers={"typ": "dpop+jwt", "jwk": public_jwk},
    )


def dpop_key_to_pem(private_key) -> str:
    """Serialize a DPoP EC private key to PEM so it survives a Celery task boundary."""
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


def dpop_key_from_pem(pem_str: str):
    """Inverse of dpop_key_to_pem — reload the EC private key inside the worker process."""
    return serialization.load_pem_private_key(pem_str.encode(), password=None)


def get_service_access_token_for_tenant(tenant, use_dpop: bool = True) -> tuple:
    """
    Obtain an Okta access token for the given tenant using Client Credentials flow.

    Args:
        tenant:    SupabaseTenant with service_client_id, service_private_key,
                   service_scopes, and either okta_issuer or okta_domain populated.
        use_dpop:  Whether to send a DPoP proof with the token request (default True).
                   Set to False when the token will be used by a client that does not
                   support DPoP (e.g. the Terraform Okta provider).  Okta binds the
                   token to the DPoP key whenever a proof is presented — even if the
                   app does not require DPoP — so the resulting token cannot be used
                   as a plain Bearer by non-DPoP-aware clients.

    Returns:
        (access_token: str, granted_scopes: list[str], dpop_key: ec.EllipticCurvePrivateKey | None)

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

    logger.info(
        f"Requesting service access token for tenant '{tenant.name}' from {token_endpoint} "
        f"(use_dpop={use_dpop})"
    )

    base_headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }

    token_data = {
        "grant_type": "client_credentials",
        "scope": tenant.service_scopes,
        "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
    }

    dpop_key = None

    if use_dpop:
        # Generate the ephemeral EC key ONCE here. The resulting access token is
        # cryptographically bound (cnf.jkt) to this key's public thumbprint, so
        # every subsequent API call with this token must present a DPoP proof
        # signed by this exact key. Generating a new key per-call would cause
        # Okta to reject all API requests with a key-mismatch error.
        dpop_key = ec.generate_private_key(ec.SECP256R1())

        # RFC 9449 §8: servers may require a server-provided nonce.
        # First attempt is sent without a nonce; if the server responds with
        # use_dpop_nonce we extract the DPoP-Nonce header and retry once.
        #
        # client_assertion carries a jti that Okta marks as used after the first
        # request, so it is regenerated on the retry; dpop_key stays the same.
        nonce = None
        for attempt in range(2):
            try:
                client_assertion = create_client_assertion_for_tenant(tenant, token_endpoint)
                dpop_proof = generate_dpop_proof("POST", token_endpoint, nonce=nonce, private_key=dpop_key)
            except Exception as e:
                raise ValueError(f"Failed to build DPoP credentials for tenant '{tenant.name}': {e}") from e

            try:
                response = requests.post(
                    token_endpoint,
                    data={**token_data, "client_assertion": client_assertion},
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
    else:
        # No DPoP — plain Bearer token suitable for clients that don't support DPoP
        # (e.g. the Terraform Okta provider).  The app must not have "Require DPoP"
        # enforced in Okta Admin Console for this to succeed.
        try:
            client_assertion = create_client_assertion_for_tenant(tenant, token_endpoint)
        except Exception as e:
            raise ValueError(f"Failed to build client assertion for tenant '{tenant.name}': {e}") from e

        try:
            response = requests.post(
                token_endpoint,
                data={**token_data, "client_assertion": client_assertion},
                headers=base_headers,
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

    return access_token, granted_scopes, dpop_key
