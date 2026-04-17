import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta

import requests
from jose import jwt

logger = logging.getLogger(__name__)

_token_cache = {"token": None, "expires_at": 0}


def _load_private_key(raw_key: str):
    """
    Load private key from either JWK JSON format or PEM format.
    Mirrors the logic in core/utils/service_token.py but without Django settings.
    """
    try:
        return json.loads(raw_key)
    except (json.JSONDecodeError, ValueError):
        return raw_key.replace("\\n", "\n")


def _create_client_assertion(client_id: str, private_key, token_endpoint: str) -> str:
    now = datetime.utcnow()
    payload = {
        "iss": client_id,
        "sub": client_id,
        "aud": token_endpoint,
        "iat": now,
        "exp": now + timedelta(hours=1),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, private_key, algorithm="RS256")


def get_access_token() -> str:
    """
    Returns a valid Bearer token for calling the Django REST API.
    Token is cached in memory and auto-refreshed 60s before expiry.

    Reads from env vars:
        OKTA_SERVICE_CLIENT_ID
        OKTA_SERVICE_PRIVATE_KEY  (JWK JSON or PEM)
        OKTA_SERVICE_SCOPES
        OKTA_API_URL
    """
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"] - 60:
        return _token_cache["token"]

    client_id = os.environ["OKTA_SERVICE_CLIENT_ID"]
    raw_key = os.environ["OKTA_SERVICE_PRIVATE_KEY"]
    scopes = os.environ["OKTA_SERVICE_SCOPES"]
    okta_api_url = os.environ["OKTA_API_URL"].rstrip("/")
    token_endpoint = f"{okta_api_url}/oauth2/v1/token"

    private_key = _load_private_key(raw_key)
    assertion = _create_client_assertion(client_id, private_key, token_endpoint)

    resp = requests.post(
        token_endpoint,
        data={
            "grant_type": "client_credentials",
            "scope": scopes,
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": assertion,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = now + data.get("expires_in", 3600)

    logger.info(f"Service token acquired. Expires in {data.get('expires_in', 3600)}s.")
    return _token_cache["token"]
