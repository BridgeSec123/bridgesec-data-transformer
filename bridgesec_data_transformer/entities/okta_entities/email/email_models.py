from mongoengine import ListField, StringField, DictField, BooleanField, IntField

from entities.models.base import BaseEntityModel


class EmailCustomization(BaseEntityModel):
    brand_id = StringField(required=False)
    template_name =  StringField(required=False)
    body = StringField(required=False)
    is_default = BooleanField(required=False)
    language = StringField(required=False)
    subject = StringField(required=False)

    meta = {"collection": "okta_email_customization"}

class EmailTemplateSettings(BaseEntityModel):
    brand_id = StringField(required=False)
    template_name = StringField(required=False)
    recipients = StringField(required=False)

    meta = {"collection": "okta_email_template_settings"}

class EmailSecurityNotification(BaseEntityModel):
    report_suspicious_activity_enabled = BooleanField(required=False)
    send_email_for_factor_enrollment_enabled = BooleanField(required=False)
    send_email_for_factor_reset_enabled = BooleanField(required=False)
    send_email_for_new_device_enabled = BooleanField(required=False)
    send_email_for_password_changed_enabled = BooleanField(required=False)

    meta = {"collection": "okta_email_notifications"}
