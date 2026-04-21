from mongoengine import StringField, DictField, ListField, BooleanField, EmbeddedDocument, EmbeddedDocumentListField

from entities.models.base import BaseEntityModel


class EntitlementBundle(BaseEntityModel):
    bundle_id = StringField(required=True)
    name = StringField(required=True)
    description = StringField(required=False)
    target_resource_orn = StringField(required=False)
    status = StringField(required=False)
    target = DictField(required=False)
    entitlements = ListField(DictField(), required=False)
    created = StringField(required=False)
    last_updated = StringField(required=False)
    created_by = StringField(required=False)
    last_updated_by = StringField(required=False)

    meta = {"collection": "okta_entitlement_bundle"}


class PrincipalEntitlement(BaseEntityModel):
    entitlement_id = StringField(required=True)
    name = StringField(required=False)
    description = StringField(required=False)
    data_type = StringField(required=False)
    multi_value = BooleanField(required=False)
    required = BooleanField(required=False)
    external_value = StringField(required=False)
    parent_resource_orn = StringField(required=False)
    target_principal_orn = StringField(required=False)
    parent = DictField(required=False)
    target_principal = DictField(required=False)
    values = ListField(DictField(), required=False)

    meta = {"collection": "okta_principal_entitlements"}


class Values(EmbeddedDocument):
    external_value = StringField(required=True)
    name = StringField(required=True)


class Entitlement(BaseEntityModel):
    data_type = StringField(required=True)
    external_value = StringField(required=True)
    multi_value = BooleanField(required=True)
    name = StringField(required=True)
    parent = DictField(required=True)
    values = EmbeddedDocumentListField(Values, required=True)
    description = StringField(required=False)

    meta = {"collection": "okta_entitlements"}
