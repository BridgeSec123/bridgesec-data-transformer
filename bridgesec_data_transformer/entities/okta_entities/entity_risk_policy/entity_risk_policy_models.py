from mongoengine import BooleanField, IntField, ListField, StringField

from entities.models.base import BaseEntityModel


class EntityRiskPolicy(BaseEntityModel):
    policy_id = StringField(required=True)
    name = StringField(required=False)
    status = StringField(required=False)

    meta = {"collection": "okta_entity_risk_policy"}


class EntityRiskPolicyRule(BaseEntityModel):
    policy_rule_id = StringField(required=True)
    policy_id = StringField(required=True)
    name = StringField(required=True)
    risk_level = StringField(required=False)
    status = StringField(required=False)
    priority = IntField(required=False, null=True)
    users_included = ListField(StringField(), required=False)
    users_excluded = ListField(StringField(), required=False)
    groups_included = ListField(StringField(), required=False)
    groups_excluded = ListField(StringField(), required=False)
    terminate_all_sessions = BooleanField(required=False, null=True)
    workflow_id = StringField(required=False, null=True)

    meta = {"collection": "okta_entity_risk_policy_rule"}
