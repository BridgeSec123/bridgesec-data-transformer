from mongoengine import ListField, StringField

from entities.models.base import BaseEntityModel

class AdminRoleCustom(BaseEntityModel):
    description = StringField(required=True)
    label = StringField(required=True)
    permissions = ListField(StringField(required=False))

    meta={'collection': 'administrators_custom_roles'}

class AdminResourceSet(BaseEntityModel):
    description = StringField(required=True)
    label = StringField(required=True)
    resources = ListField(StringField(required=False))

    meta={'collection': 'okta_resource_set'}