from mongoengine import BooleanField, ListField, StringField

from entities.models.base import BaseEntityModel


class TrustedOrigin(BaseEntityModel):
    name = StringField(required=True)
    origin = StringField(required=True)
    scopes = ListField(StringField(), required=True)
    active = BooleanField(null=True, required=False)

    meta = {"collection": "okta_trusted_origin"}