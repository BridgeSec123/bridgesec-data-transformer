from mongoengine import StringField, ListField, DictField

from entities.models.base import BaseEntityModel


class Review(BaseEntityModel):
    review_id = StringField(required=True)
    campaign_id = StringField(required=False)
    resource_id = StringField(required=False)
    reviewer_id = StringField(required=False)
    reviewer_level = StringField(required=False)
    review_ids = ListField(StringField(), required=False)
    note = StringField(required=False)
    decision = StringField(required=False)
    reviewer_type = StringField(required=False)
    current_reviewer_level = StringField(required=False)
    created = StringField(required=False)
    created_by = StringField(required=False)
    last_updated = StringField(required=False)
    last_updated_by = StringField(required=False)
    decided = StringField(required=False)
    remediation_status = StringField(required=False)
    principal_profile = DictField(required=False)

    meta = {"collection": "okta_reviews"}
