from mongoengine import StringField, DictField, ListField, BooleanField, EmbeddedDocument, EmbeddedDocumentField, EmbeddedDocumentListField

from entities.models.base import BaseEntityModel


class Target(EmbeddedDocument):
    external_id = StringField(required=True)
    type = StringField(required=True)


class EntitlementNested(EmbeddedDocument):
    id = StringField(required=True)
    values = ListField(required=True)


class Parent(EmbeddedDocument):
    external_id = StringField(required=True)
    type = StringField(required=True)


class TargetPrincipal(EmbeddedDocument):
    external_id = StringField(required=True)
    type = StringField(required=True)


class EntitlementBundle(BaseEntityModel):
    name = StringField(required=True)
    target = EmbeddedDocumentField(Target, required=True)
    entitlements = EmbeddedDocumentListField(EntitlementNested, required=True)
    description = StringField(required=False)
    target_resource_orn = StringField(required=False)
    status = StringField(required=False)

    meta = {"collection": "okta_entitlement_bundle"}


class PrincipalEntitlement(BaseEntityModel):
    parent = EmbeddedDocumentField(Parent, required=True)
    target_principal = EmbeddedDocumentField(TargetPrincipal, required=True)

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
