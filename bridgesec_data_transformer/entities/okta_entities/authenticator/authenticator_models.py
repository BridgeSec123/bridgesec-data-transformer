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

class OktaFactor(BaseEntityModel):
    provider_id = StringField(required=True)
    active = BooleanField(required=False, null=True)

    meta = {"collection": "okta_factor"}

class AuthenticatorOktaFactorTotp(BaseEntityModel):
    name = StringField(required=True)
    clock_drift_interval = IntField(required=False, null=True)
    hmac_algorithm = StringField(required=False, null=True)
    otp_length = IntField(required=False, null=True)
    shared_secret_encoding = StringField(required=False, null=True)
    time_step = IntField(required=False, null=True)

    meta = {"collection": "okta_factor_totp"}