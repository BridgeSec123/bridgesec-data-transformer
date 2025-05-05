
from mongoengine import BooleanField, IntField, StringField, ListField, DictField, EmbeddedDocumentListField, EmbeddedDocument

from entities.models.base import BaseEntityModel

class GroupsClaim(EmbeddedDocument):
    name = StringField(required=True)
    type = StringField(required=True)
    value = StringField(required=True)
    filter_type = StringField(required=False)

class JWKS(EmbeddedDocument):
    kid = StringField(required=True)
    kty = StringField(required=True)
    e = StringField(required=False)
    n = StringField(required=False)
    x = StringField(required=False)
    y = StringField(required=False)

class Timeouts(EmbeddedDocument):
    create = StringField(required=False)
    read = StringField(required=False)
    update = StringField(required=False)

class AppOauth(BaseEntityModel):
    label = StringField(required=True)
    type = StringField(required=True)
    accessibility_error_redirect_url = StringField(null=True,required=False)
    accessibility_login_redirect_url = StringField(null=True,required=False)
    accessibility_self_service = StringField(null=True,required=False)
    admin_note = StringField(null=True,required=False)
    app_links_json = StringField(null=True,required=False)
    app_settings_json = StringField(null=True,required=False)
    authentication_policy = StringField(null=True,required=False)
    auto_key_rotation = BooleanField(null=True,required=False)
    auto_submit_toolbar = BooleanField(null=True,required=False)
    client_basic_secret = StringField(null=True,required=False)
    client_id = StringField(null=True,required=False)
    client_uri = StringField(null=True,required=False)
    consent_method = StringField(null=True,required=False)
    enduser_note = StringField(null=True,required=False)
    grant_types  = ListField(null=True,required=False)
    groups_claim = EmbeddedDocumentListField(GroupsClaim, required=False)
    hide_ios = BooleanField(null=True,required=False)
    hide_web = BooleanField(null=True,required=False)
    implicit_assignment = BooleanField(null=True,required=False)
    issuer_mode = StringField(null=True,required=False)
    jwks = EmbeddedDocumentListField(JWKS, required=False)
    jwks_uri = StringField(null=True,required=False)
    login_mode = StringField(null=True,required=False)
    login_scopes = ListField(StringField(), default=list)
    login_uri = StringField(null=True,required=False)
    logo = StringField(null=True,required=False)
    logo_uri = StringField(null=True,required=False)
    omit_secret = BooleanField(null=True,required=False)
    pkce_required = BooleanField(null=True,required=False)
    policy_uri = StringField(null=True,required=False)
    post_logout_redirect_uris =  ListField( null=True,required=False)
    profile = StringField(null=True,required=False)
    redirect_uris = ListField(StringField(), default=list)
    refresh_token_leeway = IntField(null=True,required=False)
    refresh_token_rotation = StringField(null=True,required=False)
    response_types = ListField(StringField(), default=list)
    status = StringField(null=True,required=False)
    timeouts = EmbeddedDocumentListField(Timeouts, required=False)
    token_endpoint_auth_method = StringField(null=True,required=False)
    tos_uri = StringField(null=True,required=False)
    user_name_template = StringField(null=True,required=False)
    user_name_template_push_status = StringField(null=True,required=False)
    user_name_template_suffix = StringField(null=True,required=False)
    user_name_template_type = StringField(null=True,required=False)
    wildcard_redirect = StringField(null=True,required=False)

    meta = {"collection" : "okta_oauth_app"}

class AttributeStatement(EmbeddedDocument):
    name = StringField(required=True)
    filter_type = StringField(required=False)
    filter_value = StringField(required=False)
    namespace = StringField(required=False)
    type = StringField(required=True)
    values = ListField(StringField(), required=False)

class AppSAML(BaseEntityModel):
    label = StringField(required=True)
    accessibility_error_redirect_url = StringField(null=True, required=False)
    accessibility_login_redirect_url = StringField(null=True, required=False)
    accessibility_self_service = BooleanField(null=True, required=False, default=False)
    acs_endpoints = ListField(StringField(), null=True, required=False)  
    admin_note = StringField(null=True, required=False)
    app_links_json = StringField(null=True, required=False)
    app_settings_json = StringField(null=True, required=False)
    assertion_signed = BooleanField(null=True, required=False)
    attribute_statements = EmbeddedDocumentListField(AttributeStatement, required=False)
    audience = StringField(null=True, required=False)
    authentication_policy = StringField(null=True, required=False)
    authn_context_class_ref = StringField(null=True, required=False)
    auto_submit_toolbar = BooleanField(null=True, required=False, default=False)
    default_relay_state = StringField(null=True, required=False)
    destination = StringField(null=True, required=False)
    digest_algorithm = StringField(null=True, required=False)
    enduser_note = StringField(null=True, required=False)
    hide_ios = BooleanField(null=True, required=False)
    hide_web = BooleanField(null=True, required=False)
    honor_force_authn = BooleanField(null=True, required=False, default=False)
    idp_issuer = StringField(null=True, required=False)
    implicit_assignment = BooleanField(null=True, required=False)
    inline_hook_id = StringField(null=True, required=False)
    key_name = StringField(null=True, required=False)
    key_years_valid = IntField(null=True, required=False) 
    logo = StringField(null=True, required=False)
    preconfigured_app = StringField(null=True, required=False)
    recipient = StringField(null=True, required=False)
    request_compressed = BooleanField(null=True, required=False)
    response_signed = BooleanField(null=True, required=False)
    saml_signed_request_enabled = BooleanField(null=True, required=False)
    saml_version = StringField(null=True, required=False, default="2.0")
    signature_algorithm = StringField(null=True, required=False)
    single_logout_certificate = StringField(null=True, required=False)
    single_logout_issuer = StringField(null=True, required=False)
    single_logout_url = StringField(null=True, required=False)
    sp_issuer = StringField(null=True, required=False)
    sso_url = StringField(null=True, required=False)
    status = StringField(null=True, required=False, default="ACTIVE")
    subject_name_id_format = StringField(null=True, required=False)
    subject_name_id_template = StringField(null=True, required=False)
    timeouts = EmbeddedDocumentListField(Timeouts, required=False)
    user_name_template = StringField(null=True, required=False)
    user_name_template_push_status = StringField(null=True, required=False)
    user_name_template_suffix = StringField(null=True, required=False)
    user_name_template_type = StringField(null=True, required=False)
    acs_endpoints_indices = ListField(null=True, required=False)

    meta = {"collection" : "okta_saml_app"}

class GroupsClaim(EmbeddedDocument):
    id = StringField(required=True)
    priority = IntField(required=False)
    profile = DictField(required=False)

class AppGroupAssignments(BaseEntityModel):
    app_id = StringField(required=True)
    group =  EmbeddedDocumentListField(GroupsClaim, required=False)
    timeouts = EmbeddedDocumentListField(Timeouts, required=False)

    meta = {"collection" : "okta_app_group_assignment"}

class AppOAuthRoleAssignment(BaseEntityModel):
    client_id = StringField(required=True)
    type = StringField(required=True)
    resource_set = StringField(required=False)
    role = StringField(required=False)

    meta = {"collection" : "okta_app_oauth_role_assignment"}

class AppAcessPolicyAssignment(BaseEntityModel):
    app_id = StringField(required=True)
    policy_id = StringField(required=True)
    
    meta = {"collection" : "okta_app_access_policy_assignment"}

class AppPolicySignOn(BaseEntityModel):
    description = StringField(required=True)
    name = StringField(required=True)
    catch_all = BooleanField(required=False)
    priority = IntField(required=False)

    meta = {"collection" : "okta_app_policy_sign_on"}

class PlatformInclude(EmbeddedDocument):
    os_expression = StringField(required=False)
    os_type = StringField(required=False)
    type = StringField(required=False)

class AppPolicySignOnRule(BaseEntityModel):
    name = StringField(required=True)
    policy_id = StringField(required=True)
    access = StringField(required=False)
    constraints = ListField(StringField(), required=False)
    custom_expression = StringField(required=False)
    device_assurances_included = ListField(StringField(), required=False)
    device_is_managed = BooleanField(required=False)
    device_is_registered = BooleanField(required=False)
    factor_mode = StringField(required=False)
    groups_excluded = ListField(StringField(), required=False)
    groups_included = ListField(StringField(), required=False)
    inactivity_period = StringField(required=False)
    network_connection = StringField(required=False)
    network_excludes = ListField(StringField(), required=False)
    network_includes = ListField(StringField(), required=False)
    platform_include = EmbeddedDocumentListField(PlatformInclude, required=False)
    priority = IntField(required=False)
    re_authentication_frequency = StringField(required=False)
    risk_score = IntField(required=False)
    status = StringField(required=False)
    type = StringField(required=False)
    user_types_excluded = ListField(StringField(), required=False)
    user_types_included = ListField(StringField(), required=False)
    users_excluded = ListField(StringField(), required=False)
    users_included = ListField(StringField(), required=False)
    
    meta = {"collection" : "okta_app_policy_sign_on_rule"}

class AppSAMLSettings(BaseEntityModel):
    app_id = StringField(required=True)
    settings = DictField(required=False)

    meta = {"collection" : "okta_app_saml_settings"}
