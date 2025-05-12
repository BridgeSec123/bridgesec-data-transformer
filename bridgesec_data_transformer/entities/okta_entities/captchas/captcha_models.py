from mongoengine import StringField, ListField

from entities.models.base import BaseEntityModel


class Captcha(BaseEntityModel):
    name = StringField(required=True)
    type = StringField(required=True)
    site_key = StringField(required=True)
    string_key = StringField(required=True)
    
    meta = {"collection": "okta_captcha"}

class CaptchaOrgWideSettings(BaseEntityModel):
    captcha_id = StringField(required=True)
    enabled_for = ListField(StringField(), required=True)
    
    meta = {"collection": "okta_captcha_org_wide_settings"}