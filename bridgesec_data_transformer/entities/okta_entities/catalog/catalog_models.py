from mongoengine import StringField, DictField, ListField

from entities.models.base import BaseEntityModel


class CatalogEntryDefault(BaseEntityModel):
    entry_id = StringField(required=True)
    name = StringField(required=False)
    requestable = StringField(required=False)
    label = StringField(required=False)
    description = StringField(required=False)
    parent = StringField(required=False)
    counts = DictField(required=False)

    meta = {"collection": "okta_catalog_entry_default"}


class CatalogEntryUserAccessRequestFields(BaseEntityModel):
    entry_id = StringField(required=True)
    field_id = StringField(required=False)
    required = StringField(required=False)
    type = StringField(required=False)
    label = StringField(required=False)
    maximum_value = StringField(required=False)
    read_only = StringField(required=False)
    value = StringField(required=False)
    choices = ListField(StringField(), required=False)

    meta = {"collection": "okta_catalog_entry_user_access_request_fields"}


class EndUserMyRequests(BaseEntityModel):
    request_id = StringField(required=False)
    entry_id = StringField(required=True)
    status = StringField(required=False)
    requester_field_values = ListField(DictField(), required=False)

    meta = {"collection": "okta_end_user_my_requests"}
