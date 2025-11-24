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
    resource_id = StringField(required=True)
    approval_sequence_id = StringField(required=True)
    name = StringField(required=True)
    access_scope_settings = EmbeddedDocumentListField(AccessScopeSettings, required=True)
    requester_settings = EmbeddedDocumentListField(RequesterSettings, required=True)
    description = StringField(required=False)
    priority = IntField(required=False)
    access_duration_settings = EmbeddedDocumentListField(AccessDurationSettings, required=False)

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
    requested = EmbeddedDocumentField(Requested, required=True)
    requested_for = EmbeddedDocumentField(RequestedFor, required=True)
    requester_field_values = EmbeddedDocumentField(RequesterFieldValues, required=False)

    meta = {"collection": "okta_request_types"}
