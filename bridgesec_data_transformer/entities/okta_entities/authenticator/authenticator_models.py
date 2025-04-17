from mongoengine import BooleanField, IntField, StringField

from entities.models.base import BaseEntityModel


class Authenticator(BaseEntityModel):
    key = StringField()
    name = StringField()
    status = StringField(null=True,required=False)
    legacy_ignore_name = BooleanField(null=True,required=False)
    provider_auth_port = IntField(null=True,required=False)
    provider_host = StringField(null=True,required=False)
    provider_hostname = StringField(null=True,required=False)
    provider_integration_key = StringField(null=True,required=False)
    provider_json = StringField(null=True,required=False)
    provider_secret_key = StringField(null=True,required=False)
    provider_shared_secret = StringField(null=True,required=False)
    provider_user_name_template = StringField(null=True,required=False)
    settings = StringField(null=True,required=False)
    
    meta = {"collection" : "okta_authenticator"}
