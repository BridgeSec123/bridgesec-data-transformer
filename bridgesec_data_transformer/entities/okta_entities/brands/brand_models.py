
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
    
    meta = {"collection": "okta_brand"}

class EmailDomain(BaseEntityModel):
    brand_id = StringField(required=True)
    display_name = StringField(required=True)
    domain = StringField(required=True)
    user_name = StringField(required=True)

    meta = {"collection": "okta_email_domain"}


class OktaTheme(BaseEntityModel):
    brand_id = StringField(required=True)
    background_image = StringField(required=False)
    email_template_touch_point_variant = StringField(required=False)
    end_user_dashboard_touch_point_variant = StringField(required=False)
    error_page_touch_point_variant = StringField(required=False)
    favicon = StringField(required=False)
    logo = StringField(required=False)
    primary_color_contrast_hex = StringField(required=False)
    primary_color_hex = StringField(required=False)
    secondary_color_contrast_hex = StringField(required=False)
    secondary_color_hex = StringField(required=False)
    sign_in_page_touch_point_variant = StringField(required=False)
    theme_id = StringField(required=False)

    meta = {"collection": "okta_theme"}