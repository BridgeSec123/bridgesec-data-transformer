from mongoengine import DictField, StringField

from entities.models.base import BaseEntityModel


class ApiToken(BaseEntityModel):
    token_id = StringField(required=True)
    name = StringField(required=False)
    client_name = StringField(required=False)
    created = StringField(required=False)
    user_id = StringField(required=False)
    network = DictField(required=False)

    meta = {"collection": "okta_api_token"}
