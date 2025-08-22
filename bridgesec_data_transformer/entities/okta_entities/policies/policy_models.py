from mongoengine import ListField, StringField, DictField, BooleanField, IntField, EmbeddedDocumentListField, EmbeddedDocument

from entities.models.base import BaseEntityModel


class PolicyMFA(BaseEntityModel):
    id = StringField(required=True)
    name = StringField(required=True)
    description = StringField(required=False, null=True)   
    duo = DictField(required=False, null=True)
    external_idps = ListField(DictField(required=False, null=True))  
    fido_u2f = DictField(required=False, null=True)
    fido_webauthn = DictField(required=False, null=True)
    google_otp = DictField(required=False, null=True)
    groups_included = ListField(StringField(required=False, null=True))
    hotp = DictField(required=False, null=True)
    is_oie = BooleanField(required=False, null=True)
    okta_call = DictField(required=False, null=True)
    okta_email = DictField(required=False, null=True)
    okta_otp = DictField(required=False, null=True)
    okta_password = DictField(required=False, null=True)
    okta_push = DictField(required=False, null=True)
    okta_question = DictField(required=False, null=True)
    okta_sms = DictField(required=False, null=True)
    okta_verify = DictField(required=False, null=True)
    onprem_mfa = DictField(required=False, null=True)
    phone_number = DictField(required=False, null=True)
    priority = IntField(required=False, null=True)
    rsa_token = DictField(required=False, null=True)
    security_question = DictField(required=False, null=True)
    status = StringField(required=False, null=True)
    symantec_vip = DictField(required=False, null=True)
    web_authn = DictField(required=False, null=True) 
    yubikey_token = DictField(required=False, null=True)
    
    meta = {"collection": "okta_policy_mfa"}

class AppIncludeExclude(EmbeddedDocument):
    type = StringField(required=True)
    name = StringField(required=False, null=True)

class PolicyRuleMFA(BaseEntityModel):
    name = StringField(required=True)
    policy_id = StringField(required=True)
    app_exclude = EmbeddedDocumentListField(AppIncludeExclude, required=False, null=True)
    app_include = EmbeddedDocumentListField(AppIncludeExclude, required=False, null=True)
    enroll = StringField(required=False, null=True)
    network_connection = StringField(required=False, null=True)
    network_excludes = ListField(StringField(required=False, null=True))
    network_includes = ListField(StringField(required=False, null=True))
    priority = IntField(required=False, null=True)
    status = StringField(required=False, null=True)
    user_excluded = ListField(StringField(required=False, null=True))
    
    meta = {"collection": "okta_policy_rule_mfa"}


class PolicyPassword(BaseEntityModel):
    name = StringField(required=True)
    auth_provider = StringField(required=False)
    call_recovery = StringField(required=False)
    description = StringField(required=False)
    email_recovery = StringField(required=False)
    groups_included = ListField(StringField(required=False, null=True))
    password_auto_unlock_minutes = IntField(required=False, null=True)
    password_dictionary_lookup = BooleanField(required=False, null=True)
    password_exclude_first_name = BooleanField(required=False, null=True)
    password_exclude_last_name = BooleanField(required=False, null=True)
    password_exclude_username = BooleanField(required=False, null=True)
    password_expire_warn_days = IntField(required=False, null=True)
    password_history_count = IntField(required=False, null=True)
    password_lockout_notification_channels = ListField(StringField(required=False, null=True))
    password_max_age_days = IntField(required=False, null=True)
    password_max_lockout_attempts = IntField(required=False, null=True)
    password_min_age_minutes = IntField(required=False, null=True) 
    password_min_length = IntField(required=False, null=True)
    password_min_lowercase = IntField(required=False, null=True)
    password_min_number = IntField(required=False, null=True)
    password_min_symbol = IntField(required=False, null=True)
    password_min_uppercase = IntField(required=False, null=True)
    password_show_lockout_failures = BooleanField(required=False, null=True)
    priority = IntField(required=False, null=True)
    question_min_length = IntField(required=False, null=True)
    question_recovery = StringField(required=False, null=True)
    recovery_email_token = StringField(required=False, null=True)
    skip_unlock = BooleanField(required=False, null=True)
    sms_recovery = StringField(required=False, null=True)
    status = StringField(required=False, null=True)

    meta={"collection": "okta_policy_password"}

class PolicyProfileEnrollment(BaseEntityModel):
    id = StringField(required=True)
    name = StringField(required=True)
    status = StringField(required=False, null=True)
    
    meta={"collection": "okta_policy_profile_enrollment"}

class PolicyProfileEnrollmentApps(BaseEntityModel):
    policy_id = StringField(required=True)
    apps = ListField(StringField(required=False, null=True))
    
    meta = {"collection": "okta_policy_profile_enrollment_apps"}

class Platform(EmbeddedDocument):
    type = StringField(required=False)
    os_expression = StringField(required=False)
    os_type = StringField(required=False)

class IdentifierPattern(EmbeddedDocument):
    match_type = StringField(required=False)
    value = StringField(required=False)

class PolicyRuleIDPDiscovery(BaseEntityModel):
    name = StringField(required=True)
    policy_id = StringField(required=False, null=True)
    app_exclude = EmbeddedDocumentListField(AppIncludeExclude, required=False, null=True)
    app_include = EmbeddedDocumentListField(AppIncludeExclude, required=False, null=True)
    idp_id = StringField(required=False, null=True)
    idp_type = StringField(required=False, null=True)
    network_connection = StringField(required=False, null=True)
    network_excludes = ListField(StringField(required=False, null=True))
    network_includes = ListField(StringField(required=False, null=True))
    platform_include = EmbeddedDocumentListField(Platform)
    priority = IntField(required=False, null=True)
    status = StringField(required=False, null=True)
    user_identifier_attribute = StringField(required=False, null=True)
    user_identifier_patterns = EmbeddedDocumentListField(IdentifierPattern, required=False, null=True)
    user_identifier_type = StringField(required=False, null=True)

    meta = {"collection": "okta_policy_rule_idp_discovery"}

class PolicyRulePassword(BaseEntityModel):
    name = StringField(required=True)
    policy_id = StringField(required=False, null=True)
    network_connection = StringField(required=False, null=True)
    network_excludes = ListField(StringField(required=False, null=True))
    network_includes = ListField(StringField(required=False, null=True))
    password_change = StringField(required=False, null=True)
    password_reset = StringField(required=False, null=True)
    password_unlock = StringField(required=False, null=True)
    priority = IntField(required=False, null=True)
    status = StringField(required=False, null=True)
    user_excluded = ListField(StringField(required=False, null=True))

    meta = {"collection": "okta_policy_rule_password"}

class ProfileAttributes(EmbeddedDocument):
    label = StringField(required=True)
    name = StringField(required=False, null=True)
    required = BooleanField(required=True)

class PolicyRuleProfileEnrollment(BaseEntityModel):
    policy_id = StringField(required=True)
    unknown_user_action = StringField(required=True)
    access = StringField(required=False, null=True)
    email_verification = StringField(required=False, null=True)
    enroll_authenticator_types = StringField(required=False, null=True)
    inline_hook_id = StringField(required=False, null=True)
    profile_attributes = EmbeddedDocumentListField(ProfileAttributes, required=False, null=True)
    progressive_profiling_action = StringField(required=False, null=True)
    target_group_id = StringField(required=False, null=True)
    ui_schema_id = StringField(required=False, null=True)

    meta = {"collection": "okta_policy_rule_profile_enrollment"}

class PolicySignOn(BaseEntityModel):
    name = StringField(required=True)
    description = StringField(required=False, null=True)
    groups_included = ListField(StringField(required=False, null=True))
    priority = IntField(required=False, null=True)
    status = StringField(required=False, null=True)
    
    meta = {"collection": "okta_policy_sign_on"}

class FactorSequence(EmbeddedDocument):
    primary_criteria_provider = StringField(required=True)
    primary_criteria_factor_type = StringField(required=True)
    secondary_criteria = StringField(required=False, null=True)
    provider = StringField(required=True)
    factor_type = StringField(required=True)

class PolicyRuleSignOn(BaseEntityModel):
    name = StringField(required=True)
    access = StringField(required=False, null=True)
    auth_type = StringField(required=False, null=True)
    behaviors = ListField(StringField(required=False, null=True))
    factor_sequence = EmbeddedDocumentListField(FactorSequence)
    identity_provider = StringField(required=False, null=True)
    identity_provider_ids = ListField(StringField(required=False, null=True))
    mfa_prompt = StringField(required=False, null=True)
    mfa_lifetime = IntField(required=False, null=True)
    mfa_remember_device = BooleanField(required=False, null=True)
    mfa_required = BooleanField(required=False, null=True)
    policy_id = StringField(required=False, null=True)
    network_connection = StringField(required=False, null=True)
    network_excludes = ListField(StringField(required=False, null=True))
    network_includes = ListField(StringField(required=False, null=True))
    primary_factor = StringField(required=False, null=True)
    priority = IntField(required=False, null=True)
    risk_level = StringField(required=False, null=True)
    session_idle = IntField(required=False, null=True)
    session_lifetime = IntField(required=False, null=True)
    session_persistent = BooleanField(required=False, null=True)
    status = StringField(required=False, null=True)
    users_excluded = ListField(StringField(required=False, null=True))
    
    meta = {"collection": "okta_policy_rule_sign_on"}
