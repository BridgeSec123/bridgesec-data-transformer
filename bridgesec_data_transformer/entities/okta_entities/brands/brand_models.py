
from entities.models.base import BaseEntityModel
from mongoengine import StringField, BooleanField

class Brand(BaseEntityModel):
    name = StringField(required=True)
    agree_to_custom_privacy_policy = BooleanField(required=False, null=True)
    brand_id = StringField(required=False, null=True)
    custom_privacy_policy_url = StringField(required=False, null=True)
    default_app_app_instance_id = StringField(required=False, null=True)
    default_app_app_link_name = StringField(required=False, null=True)
    default_app_classic_application_uri = StringField(required=False, null=True)
    locale = StringField(required=False, null=True)
    remove_powered_by_okta = BooleanField(required=False, null=True)
    
    meta = {"collection": "okta_brand"}

class EmailDomain(BaseEntityModel):
    brand_id = StringField(required=True)
    display_name = StringField(required=True)
    domain = StringField(required=True)
    user_name = StringField(required=True)

    meta = {"collection": "okta_email_domain"}


class OktaTheme(BaseEntityModel):
    brand_id = StringField(required=True)
    background_image = StringField(required=False, null=True)
    email_template_touch_point_variant = StringField(required=False, null=True)
    end_user_dashboard_touch_point_variant = StringField(required=False, null=True)
    error_page_touch_point_variant = StringField(required=False, null=True)
    favicon = StringField(required=False, null=True)
    logo = StringField(required=False, null=True)
    primary_color_contrast_hex = StringField(required=False, null=True)
    primary_color_hex = StringField(required=False, null=True)
    secondary_color_contrast_hex = StringField(required=False, null=True)
    secondary_color_hex = StringField(required=False, null=True)
    sign_in_page_touch_point_variant = StringField(required=False, null=True)
    theme_id = StringField(required=False, null=True)

    meta = {"collection": "okta_theme"}