from mongoengine import StringField, DictField, ListField

from entities.models.base import BaseEntityModel


class CatalogEntryDefault(BaseEntityModel):
    entry_id = StringField(required=True)

    meta = {"collection": "okta_catalog_entry_default"}


class CatalogEntryUserAccessRequestFields(BaseEntityModel):
    entry_id = StringField(required=True)
    user_id = StringField(required=True)

    meta = {"collection": "okta_catalog_entry_user_access_request_fields"}


class EndUserMyRequests(BaseEntityModel):
    entry_id = StringField(required=True)
    id = StringField(required=False)
    requester_field_values = ListField(DictField(), required=False)

    meta = {"collection": "okta_end_user_my_requests"}
