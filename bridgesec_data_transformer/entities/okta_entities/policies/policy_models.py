from mongoengine import ListField, StringField, DictField, BooleanField, IntField

from entities.models.base import BaseEntityModel


class PolicyMFA(BaseEntityModel):
    name = StringField(required=True)
    description = StringField(required=False)   
    duo = DictField(required=False)
    external_idps = ListField(DictField(required=False))  
    fido_u2f = DictField(required=False)
    fido_webauthn = DictField(required=False)
    google_otp = DictField(required=False)
    groups_included = ListField(StringField(required=False))
    hotp = DictField(required=False)
    is_oie = BooleanField(required=False)
    okta_call = DictField(required=False)
    okta_email = DictField(required=False)
    okta_otp = DictField(required=False)
    okta_password = DictField(required=False)
    okta_push = DictField(required=False)
    okta_question = DictField(required=False)
    okta_sms = DictField(required=False)
    okta_verify = DictField(required=False)
    onprem_mfa = DictField(required=False)
    phone_number = DictField(required=False)
    priority = IntField(required=False)
    rsa_token = DictField(required=False)
    security_question = DictField(required=False)
    status = StringField(required=False)
    symantec_vip = DictField(required=False)
    web_authn = DictField(required=False) 
    yubikey_token = DictField(required=False)
    
    meta = {"collection": "okta_policy_mfa"}


class PolicyPassword(BaseEntityModel):
    name = StringField(required=True)
    auth_provider = StringField(required=False)
    call_recovery = StringField(required=False)
    description = StringField(required=False)
    email_recovery = StringField(required=False)
    groups_included = ListField(StringField(required=False))
    password_auto_unlock_minutes = IntField(required=False)
    password_dictionary_lookup = BooleanField(required=False)
    password_exclude_first_name = BooleanField(required=False)
    password_exclude_last_name = BooleanField(required=False)
    password_exclude_username = BooleanField(required=False)
    password_expire_warn_days = IntField(required=False)
    password_history_count = IntField(required=False)
    password_lockout_notification_channels = ListField(StringField(required=False))
    password_max_age_days = IntField(required=False)
    password_max_lockout_attempts = IntField(required=False)
    password_min_age_minutes = IntField(required=False) 
    password_min_length = IntField(required=False)
    password_min_lowercase = IntField(required=False)
    password_min_number = IntField(required=False)
    password_min_symbol = IntField(required=False)
    password_min_uppercase = IntField(required=False)
    password_show_lockout_failures = BooleanField(required=False)
    priority = IntField(required=False)
    question_min_length = IntField(required=False)
    question_recovery = StringField(required=False)
    recovery_email_token = StringField(required=False)
    skip_unlock = BooleanField(required=False)
    sms_recovery = StringField(required=False)
    status = StringField(required=False)
    
    meta={"collection": "okta_policy_password"}

class PolicyProfileEnrollment(BaseEntityModel):
    id = StringField(required=True)
    name = StringField(required=True)
    status = StringField(required=False)
    
    meta={"collection": "okta_policy_profile_enrollment"}

class PolicyProfileEnrollmentApps(BaseEntityModel):
    policy_id = StringField(required=True)
    apps = ListField(StringField(required=False))
    
    meta = {"collection": "okta_policy_profile_enrollment_apps"}