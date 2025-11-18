from mongoengine import BooleanField, IntField, StringField

from entities.models.base import BaseEntityModel


class EmailSmtpServer(BaseEntityModel):
    smtp_id = StringField(required=True)
    alias = StringField(required=True)
    host = StringField(required=True)
    port = IntField(required=True)
    username = StringField(required=True)
    password = StringField(required=True)
    enabled = BooleanField(required=False)

    meta = {"collection": "okta_email_smtp_server"}


class EmailCustomization(BaseEntityModel):
    brand_id = StringField(required=True)
    template_name =  StringField(required=True)
    body = StringField(required=False)
    is_default = BooleanField(required=False)
    language = StringField(required=False)
    subject = StringField(required=False)

    meta = {"collection": "okta_email_customization"}

class EmailTemplateSettings(BaseEntityModel):
    brand_id = StringField(required=True)
    template_name = StringField(required=True)
    recipients = StringField(required=True)

    meta = {"collection": "okta_email_template_settings"}

class EmailSecurityNotification(BaseEntityModel):
    report_suspicious_activity_enabled = BooleanField(required=False)
    send_email_for_factor_enrollment_enabled = BooleanField(required=False)
    send_email_for_factor_reset_enabled = BooleanField(required=False)
    send_email_for_new_device_enabled = BooleanField(required=False)
    send_email_for_password_changed_enabled = BooleanField(required=False)

    meta = {"collection": "okta_security_notification_emails"}
