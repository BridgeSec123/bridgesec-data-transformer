import logging
import os
from typing import Any

import requests
from auth import get_access_token

logger = logging.getLogger(__name__)

BASE_URL = os.environ.get("BRIDGESEC_API_URL", "http://localhost:8000").rstrip("/")


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {get_access_token()}",
        "Content-Type": "application/json",
    }


def get(path: str, params: dict = None) -> Any:
    url = f"{BASE_URL}{path}"
    logger.debug(f"GET {url} params={params}")
    resp = requests.get(url, headers=_headers(), params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def post(path: str, body: dict | list = None, params: dict = None) -> Any:
    url = f"{BASE_URL}{path}"
    logger.debug(f"POST {url} params={params}")
    resp = requests.post(url, headers=_headers(), json=body or {}, params=params, timeout=60)
    resp.raise_for_status()
    return resp.json()
