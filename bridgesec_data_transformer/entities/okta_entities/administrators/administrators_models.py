from mongoengine import BooleanField, IntField, ListField, StringField

from entities.models.base import BaseEntityModel

class AdminRoleCustom(BaseEntityModel):
    description = StringField(required=True)
    label = StringField(required=True)
    permissions = ListField(StringField(required=False))

    meta={'collection': 'administrators_custom_roles'}
    

class AdminResourseset(BaseEntityModel):
    description = StringField(required=True)
    label = StringField(required=True)
    resources = ListField(StringField(required=False))

    meta={'collection': 'okta_resource_set'}