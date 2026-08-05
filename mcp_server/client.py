import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)

BASE_URL = os.environ.get("BRIDGESEC_API_URL", "http://localhost:8000").rstrip("/")


def _headers(token: str) -> dict:
    """
    Build request headers using the caller's own bearer token.

    The MCP server no longer holds a service-app identity — every request is
    made AS the user who invoked the tool, so Django resolves their tenant,
    roles, and OPA policies exactly as it would for a normal API call.
    """
    if not token:
        raise ValueError(
            "No caller token available. The MCP server forwards the user's bearer "
            "token to the API and has no service-app fallback."
        )
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def get(path: str, token: str, params: dict = None) -> Any:
    url = f"{BASE_URL}{path}"
    logger.debug(f"GET {url} params={params}")
    resp = requests.get(url, headers=_headers(token), params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def post(path: str, token: str, body: dict | list = None, params: dict = None) -> Any:
    url = f"{BASE_URL}{path}"
    logger.debug(f"POST {url} params={params}")
    resp = requests.post(url, headers=_headers(token), json=body or {}, params=params, timeout=60)
    resp.raise_for_status()
    return resp.json()


def put(path: str, token: str, body: dict | list = None, params: dict = None) -> Any:
    url = f"{BASE_URL}{path}"
    logger.debug(f"PUT {url} params={params}")
    resp = requests.put(url, headers=_headers(token), json=body or {}, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()
