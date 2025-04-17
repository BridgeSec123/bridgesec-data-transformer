from mongoengine import DictField, StringField

from entities.models.base import BaseEntityModel


class InlineHook(BaseEntityModel):
    name = StringField(required=True)
    version = StringField(required=True)
    type = StringField(required=True)
    channel = DictField(null=True, required=False)
    channel_json = DictField(null=True, required=False)
    status = StringField(null=True, required=False)
    auth = DictField(null=True, required=False)
    
    meta = {"collection": "inline_hooks"}