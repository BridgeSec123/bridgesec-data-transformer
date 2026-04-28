import re


# Base aggregation policy (pushed with ID = "base") — deny-overrides-allow semantics.
# A deny rule blocks the request even if an allow rule would pass.
BASE_REGO = """package authz

import future.keywords.if
import future.keywords.in

default allow := false

allow if {
    allows
    not denies
}

allows if {
    some p
    data.authz.rules[p].allow
}

denies if {
    some p
    data.authz.rules[p].deny
}
"""


def _safe_id(policy_id: str) -> str:
    """Sanitize a UUID or arbitrary string for use as a Rego package name segment."""
    return re.sub(r"[^a-zA-Z0-9_]", "_", policy_id)


def _format_value(value) -> str:
    """Format a Python value for inclusion in a Rego expression."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    # default: treat as string
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def translate(rule) -> str:
    """
    Translate a PolicyRule-like object into Rego source text.

    Accepts any object exposing: policy_id, role, entity, action, effect, conditions.
    """
    safe_id = _safe_id(rule.policy_id)
    pkg = f"authz.rules.policy_{safe_id}"
    rule_keyword = getattr(rule, "effect", "allow") or "allow"
    conds = getattr(rule, "conditions", None) or {}

    conditions = []

    role = getattr(rule, "role", "*")
    entity = getattr(rule, "entity", "*")
    action = getattr(rule, "action", "*")

    if role and role != "*":
        conditions.append(f'input.user.role == "{role}"')
    if entity and entity != "*":
        conditions.append(f'input.entity == "{entity}"')
    if action and action != "*":
        conditions.append(f'input.action == "{action}"')

    # exclude_actions — block specific HTTP actions
    excluded = conds.get("exclude_actions", []) or []
    if excluded:
        if len(excluded) == 1:
            conditions.append(f'input.action != "{excluded[0]}"')
        else:
            values = ", ".join(f'"{a}"' for a in excluded)
            conditions.append(f"not input.action in {{{values}}}")

    # own_records_only — created_by == user.email
    if conds.get("own_records_only"):
        conditions.append(
            "input.resource_attributes.created_by == input.user.email"
        )

    # field_conditions — fires only when resource_attributes is populated (detail views)
    field_conditions = conds.get("field_conditions", {}) or {}
    for field, value in field_conditions.items():
        conditions.append(
            f'input.resource_attributes["{field}"] == {_format_value(value)}'
        )

    # record_id_filter — fires only when resource_id matches a specific ID
    id_filter = conds.get("record_id_filter", []) or []
    if id_filter:
        if len(id_filter) == 1:
            conditions.append(f'input.resource_id == "{id_filter[0]}"')
        else:
            values = ", ".join(f'"{v}"' for v in id_filter)
            conditions.append(f"input.resource_id in {{{values}}}")

    body = "\n    ".join(conditions) if conditions else "true"

    return (
        f"package {pkg}\n\n"
        f"import future.keywords.if\n"
        f"import future.keywords.in\n\n"
        f"{rule_keyword} if {{\n    {body}\n}}\n"
    )
