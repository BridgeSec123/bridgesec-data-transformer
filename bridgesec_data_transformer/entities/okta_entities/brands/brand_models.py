
from entities.models.base import BaseEntityModel
from mongoengine import StringField, BooleanField

class Brand(BaseEntityModel):
    name = StringField(required=True)
    agree_to_custom_privacy_policy = BooleanField(required=False)
    brand_id = StringField(required=False)
    custom_privacy_policy_url = StringField(required=False)
    default_app_app_instance_id = StringField(required=False)
    default_app_app_link_name = StringField(required=False)
    default_app_classic_application_uri = StringField(required=False)
    locale = StringField(required=False)
    remove_powered_by_okta = BooleanField(required=False)
    
    meta = {"collection": "brands"}
