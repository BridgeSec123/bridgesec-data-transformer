from mongoengine import BooleanField, StringField

from entities.models.base import BaseEntityModel


class HookKey(BaseEntityModel):
    hook_key_id = StringField(required=True)
    name = StringField(required=True)
    key_id = StringField(required=False)
    created = StringField(required=False)
    is_used = BooleanField(required=False)
    last_updated = StringField(required=False)

    meta = {"collection": "okta_hook_key"}
