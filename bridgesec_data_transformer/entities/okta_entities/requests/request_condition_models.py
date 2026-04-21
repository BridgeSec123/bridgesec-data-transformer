from mongoengine import StringField, IntField, ListField, DictField, EmbeddedDocument, EmbeddedDocumentListField, EmbeddedDocumentField

from entities.models.base import BaseEntityModel


class AccessScopeSettings(EmbeddedDocument):
    type = StringField(required=True)
    id = ListField(StringField(), required=True)


class RequesterSettings(EmbeddedDocument):
    type = StringField(required=True)
    id = ListField(StringField(), required=True)


class AccessDurationSettings(EmbeddedDocument):
    type = StringField(required=True)
    duration = StringField(required=True)


class RequestCondition(BaseEntityModel):
    condition_id = StringField(required=True)
    resource_id = StringField(required=True)
    approval_sequence_id = StringField(required=False)
    name = StringField(required=True)
    status = StringField(required=False)
    priority = IntField(required=False)
    description = StringField(required=False)
    created = StringField(required=False)
    created_by = StringField(required=False)
    last_updated = StringField(required=False)
    last_updated_by = StringField(required=False)
    access_scope_settings = ListField(DictField(), required=False)
    requester_settings = ListField(DictField(), required=False)
    access_duration_settings = ListField(DictField(), required=False)

    meta = {"collection": "okta_request_conditions"}


class RequestSequence(BaseEntityModel):
    resource_id = StringField(required=True)
    sequence_id = StringField(required=True, max_length=24)

    meta = {"collection": "okta_request_sequences"}


class RequestSettings(BaseEntityModel):
    resource_id = StringField(required=True)

    meta = {"collection": "okta_request_settings"}


class Requested(EmbeddedDocument):
    entry_id = StringField(required=True)
    type = StringField(required=True)
    access_scope_id = StringField(required=False)
    access_scope_type = StringField(required=False)
    resource_id = StringField(required=False)
    resource_type = StringField(required=False)


class RequestedFor(EmbeddedDocument):
    external_id = StringField(required=True)
    type = StringField(required=True)


class RequesterFieldValues(EmbeddedDocument):
    id = StringField(required=False)
    label = StringField(required=False)
    type = StringField(required=False)
    value = StringField(required=False)
    values = ListField(StringField(), required=False)


class RequestType(BaseEntityModel):
    request_id = StringField(required=True)
    requested = DictField(required=True)
    requested_for = DictField(required=True)
    requester_field_values = DictField(required=False)
    status = StringField(required=False)
    created = StringField(required=False)
    created_by = StringField(required=False)
    last_updated = StringField(required=False)
    last_updated_by = StringField(required=False)
    access_duration = StringField(required=False)
    granted = StringField(required=False)
    grant_status = StringField(required=False)
    resolved = StringField(required=False)
    revocation_scheduled = StringField(required=False)
    revocation_status = StringField(required=False)
    revoked = StringField(required=False)

    meta = {"collection": "okta_request_types"}
