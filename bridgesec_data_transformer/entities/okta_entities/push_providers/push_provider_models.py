from entities.models.base import BaseEntityModel
from mongoengine import DictField, StringField


class PushProvider(BaseEntityModel):
    push_provider_id = StringField(required=True)
    name = StringField(required=True)
    provider_type = StringField(required=True)
    last_updated_date = StringField(required=False)
    configuration = DictField(required=False)

    meta = {"collection": "okta_push_provider"}
