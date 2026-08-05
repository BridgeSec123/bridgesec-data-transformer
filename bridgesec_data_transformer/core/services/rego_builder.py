import re


# Base aggregation policy (pushed with ID = "base") — deny-overrides-allow semantics.
# A deny rule blocks the request even if an allow rule would pass.
BASE_REGO = """package authz

import future.keywords.if
import future.keywords.in

default allow := false

# Super admins bypass all policy checks
allow if {
    "super_admin" in input.user.roles
}

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
        # Support both legacy single-role field and new multi-role array
        conditions.append(f'"{role}" in input.user.roles')

    # subject_type == "user" targets ONE specific person by email, ANDed with any
    # role line above (both must hold). role="*" + subject → user-only rule.
    subject_type = getattr(rule, "subject_type", "role") or "role"
    subject = getattr(rule, "subject", None)
    if subject_type == "user" and subject:
        conditions.append(f'input.user.email == "{subject}"')

    if entity and entity != "*":
        conditions.append(f'input.entity == "{entity}"')
    if action and action != "*":
        conditions.append(f'input.action == "{action}"')

    # Tenant-specific rule: only fires for users in the matching tenant.
    # Global rules (tenant_id=None) have no such condition and apply to all tenants.
    tenant_id = getattr(rule, "tenant_id", None)
    if tenant_id:
        conditions.append(f'input.user.tenant_id == "{tenant_id}"')

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


def demo():
    import types
    # user + data + id combo → all conditions ANDed in one deny rule
    rego = translate(types.SimpleNamespace(
        policy_id="p1", role="*", entity="apps", action="delete", effect="deny",
        subject_type="user", subject="alice@corp.com",
        conditions={"field_conditions": {"label": "Prod"}, "record_id_filter": ["0oa1"]},
    ))
    assert 'input.user.email == "alice@corp.com"' in rego
    assert 'input.entity == "apps"' in rego
    assert 'input.resource_attributes["label"] == "Prod"' in rego
    assert 'input.resource_id == "0oa1"' in rego
    assert '"*" in input.user.roles' not in rego          # wildcard role emits no line
    assert rego.strip().startswith("package authz.rules.policy_p1")

    # subject_type="role" (default) must NOT emit an email line
    rego_role = translate(types.SimpleNamespace(
        policy_id="p2", role="admin", entity="users", action="update", effect="deny",
    ))
    assert "input.user.email" not in rego_role
    assert '"admin" in input.user.roles' in rego_role
    print("rego_builder demo OK")


if __name__ == "__main__":
    demo()
