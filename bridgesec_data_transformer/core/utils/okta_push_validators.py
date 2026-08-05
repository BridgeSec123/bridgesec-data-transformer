"""
Input validators for the okta-push endpoint.

Scope names, group names, and policy names go directly into Okta API calls.
Validate them here before any Okta request is made.
"""
import re

_SCOPE_NAME_RE = re.compile(r'^[a-zA-Z0-9:_\-\.]+$')
_LOCALHOST_ORIGINS = ("http://localhost", "http://127.0.0.1")


def _is_valid_redirect_uri(uri: str) -> bool:
    """https:// always allowed; http:// only for localhost / 127.0.0.1 (dev URIs)."""
    if uri.startswith("https://"):
        return True
    return any(uri.startswith(origin) for origin in _LOCALHOST_ORIGINS)
_LABEL_RE = re.compile(r'^[a-zA-Z0-9 _\-\.]+$')
_MAX_NAME_LEN = 255
_MAX_DESC_LEN = 1024


def validate_scope_name(name: str) -> str | None:
    """Return error message or None if valid."""
    if not name or not isinstance(name, str):
        return "scope name must be a non-empty string"
    if len(name) > _MAX_NAME_LEN:
        return f"scope name exceeds {_MAX_NAME_LEN} characters"
    if not _SCOPE_NAME_RE.match(name):
        return f"scope name '{name}' contains invalid characters (allowed: a-z A-Z 0-9 : _ - .)"
    return None


def validate_label(label: str, field: str = "label") -> str | None:
    """Return error message or None if valid."""
    if not label or not isinstance(label, str):
        return f"{field} must be a non-empty string"
    if len(label) > _MAX_NAME_LEN:
        return f"{field} exceeds {_MAX_NAME_LEN} characters"
    if not _LABEL_RE.match(label):
        return f"{field} '{label}' contains invalid characters (allowed: a-z A-Z 0-9 space _ - .)"
    return None


def validate_description(desc: str) -> str | None:
    """Return error message or None if valid."""
    if not isinstance(desc, str):
        return "description must be a string"
    if len(desc) > _MAX_DESC_LEN:
        return f"description exceeds {_MAX_DESC_LEN} characters"
    if any(ord(c) < 32 and c not in ('\t', '\n') for c in desc):
        return "description contains invalid control characters"
    return None


def validate_push_payload(data: dict) -> list[str]:
    """
    Validate the entire okta-push request body.

    Accepts either a single app config (existing flat shape) or a bulk
    payload of the form {"apps": [<app config>, ...]} to modify several
    apps for the same tenant in one call.

    Returns a list of error strings — empty list means valid.
    """
    if not isinstance(data, dict):
        return ["request body must be a JSON object"]

    apps = data.get("apps")
    if apps is not None:
        if not isinstance(apps, list) or not apps:
            return ["apps must be a non-empty list"]
        errors = []
        for i, app_config in enumerate(apps):
            if not isinstance(app_config, dict):
                errors.append(f"apps[{i}]: must be a JSON object")
                continue
            errors.extend(f"apps[{i}].{e}" for e in _validate_app_config(app_config))
        return errors

    return _validate_app_config(data)


def _validate_app_config(data: dict) -> list[str]:
    """Validate a single app config (scopes/app/groups/policies)."""
    errors = []

    # Validate scopes
    for i, scope in enumerate(data.get("scopes") or []):
        prefix = f"scopes[{i}]"
        err = validate_scope_name(scope.get("name", ""))
        if err:
            errors.append(f"{prefix}.name: {err}")
        if "description" in scope:
            err = validate_description(scope["description"])
            if err:
                errors.append(f"{prefix}.description: {err}")
        if "consent" in scope and scope["consent"] not in ("REQUIRED", "IMPLICIT", "FLEXIBLE"):
            errors.append(f"{prefix}.consent: must be REQUIRED, IMPLICIT, or FLEXIBLE")

    # Validate app
    app = data.get("app") or {}
    if app:
        if "label" in app:
            err = validate_label(app["label"], "app.label")
            if err:
                errors.append(err)
        for j, uri in enumerate(app.get("redirect_uris") or []):
            if not isinstance(uri, str) or not _is_valid_redirect_uri(uri):
                errors.append(
                    f"app.redirect_uris[{j}]: must be https:// or http://localhost / http://127.0.0.1"
                )

    # Validate groups
    for i, group in enumerate(data.get("groups") or []):
        prefix = f"groups[{i}]"
        err = validate_label(group.get("name", ""), f"{prefix}.name")
        if err:
            errors.append(err)
        if "description" in group:
            err = validate_description(group["description"])
            if err:
                errors.append(f"{prefix}.description: {err}")

    # Validate policies
    for i, policy in enumerate(data.get("policies") or []):
        prefix = f"policies[{i}]"
        err = validate_label(policy.get("name", ""), f"{prefix}.name")
        if err:
            errors.append(err)
        for j, rule in enumerate(policy.get("rules") or []):
            err = validate_label(rule.get("name", ""), f"{prefix}.rules[{j}].name")
            if err:
                errors.append(err)

    return errors
