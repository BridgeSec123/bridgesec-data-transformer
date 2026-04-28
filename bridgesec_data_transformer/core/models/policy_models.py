from mongoengine import (
    DateTimeField,
    DictField,
    Document,
    StringField,
)


class PolicyRule(Document):
    """
    Structured authorization policy — translated to Rego and pushed to OPA.

    `conditions` supported keys:
        own_records_only:  bool               — created_by == user.email
        exclude_actions:   list[str]          — block specific HTTP actions
        field_conditions:  dict[str, Any]     — resource_attributes[field] == value (detail views)
        record_id_filter:  list[str]          — resource_id in {id1, id2, ...}
    """

    policy_id   = StringField(primary_key=True)          # UUID, used as OPA policy ID
    name        = StringField(required=True)
    description = StringField()
    role        = StringField(required=True)             # "admin" | "user" | "*"
    entity      = StringField(required=True)             # "apps" | "users" | "*"
    action      = StringField(required=True)             # "read" | "create" | "update" | "delete" | "*"
    effect      = StringField(choices=["allow", "deny"], default="allow")
    conditions  = DictField()
    rego_source = StringField(required=True)             # compiled Rego text pushed to OPA
    created_by  = StringField()
    created_at  = DateTimeField()
    updated_at  = DateTimeField()

    meta = {
        "collection": "opa_policy_rules",
        "alias": "bridgesec",
    }
