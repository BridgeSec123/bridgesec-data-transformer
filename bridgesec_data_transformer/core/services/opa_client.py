import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _base_url() -> str:
    return getattr(settings, "OPA_URL", "http://localhost:8181").rstrip("/")


def _timeout() -> float:
    return float(getattr(settings, "OPA_TIMEOUT_SEC", 2))


def query(input_data: dict) -> bool:
    """Policy decision — enforcement hot path. Fail-closed on error."""
    try:
        r = requests.post(
            f"{_base_url()}/v1/data/authz/allow",
            json={"input": input_data},
            timeout=_timeout(),
        )
        if r.status_code != 200:
            logger.warning(
                "OPA returned non-200",
                extra={"component": "opa", "status_code": r.status_code, "body": r.text[:200]},
            )
            return False
        return r.json().get("result") is True
    except Exception as e:
        logger.error(
            "OPA query failed",
            extra={"component": "opa", "error": str(e)},
        )
        return False  # fail-closed


def push_policy(policy_id: str, rego_text: str) -> None:
    """Upload or replace a policy. PUT is idempotent."""
    r = requests.put(
        f"{_base_url()}/v1/policies/{policy_id}",
        data=rego_text.encode("utf-8"),
        headers={"Content-Type": "text/plain"},
        timeout=_timeout(),
    )
    r.raise_for_status()
    logger.info(
        "OPA policy pushed",
        extra={"component": "opa", "policy_id": policy_id},
    )


def delete_policy(policy_id: str) -> None:
    """Delete a policy from OPA. 404 is treated as success (already gone)."""
    r = requests.delete(
        f"{_base_url()}/v1/policies/{policy_id}",
        timeout=_timeout(),
    )
    if r.status_code not in (200, 404):
        r.raise_for_status()
    logger.info(
        "OPA policy deleted",
        extra={"component": "opa", "policy_id": policy_id, "status_code": r.status_code},
    )


def list_policies() -> list:
    """Return list of policy IDs currently loaded in OPA."""
    r = requests.get(f"{_base_url()}/v1/policies", timeout=_timeout())
    r.raise_for_status()
    return [p["id"] for p in r.json().get("result", [])]


def get_policy(policy_id: str) -> str:
    """Fetch the raw Rego text of a policy from OPA."""
    r = requests.get(f"{_base_url()}/v1/policies/{policy_id}", timeout=_timeout())
    r.raise_for_status()
    return r.json().get("result", {}).get("raw", "")
