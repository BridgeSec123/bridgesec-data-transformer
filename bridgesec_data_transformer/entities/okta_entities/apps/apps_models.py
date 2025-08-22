
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
    app_id = StringField(required=True)
    label = StringField(required=True)
    type = StringField(required=True)
    accessibility_error_redirect_url = StringField(null=True,required=False)
    accessibility_login_redirect_url = StringField(null=True,required=False)
    accessibility_self_service = StringField(null=True,required=False)
    admin_note = StringField(null=True,required=False)
    app_links_json = StringField(null=True,required=False)
    app_settings_json = DictField(null=True,required=False)
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

    meta = {"collection" : "okta_app_oauth"}

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

    meta = {"collection" : "okta_app_saml"}

class GroupsClaim(EmbeddedDocument):
    id = StringField(required=True, null=True) 
    priority = IntField(required=False, null=True)
    profile = DictField(required=False, null=True)

class AppGroupAssignments(BaseEntityModel):
    app_id = StringField(required=True)
    group =  EmbeddedDocumentListField(GroupsClaim, required=False)
    timeouts = EmbeddedDocumentListField(Timeouts, required=False)

    meta = {"collection" : "okta_app_group_assignments"}

class AppOAuthRoleAssignment(BaseEntityModel):
    client_id = StringField(required=True)
    type = StringField(required=True)
    resource_set = StringField(required=False, null=True)
    role = StringField(required=False, null=True)

    meta = {"collection" : "okta_app_oauth_role_assignment"}

class AppAccessPolicyAssignment(BaseEntityModel):
    app_id = StringField(required=True)
    policy_id = StringField(required=True)
    
    meta = {"collection" : "okta_app_access_policy_assignment"}

class AppPolicySignOn(BaseEntityModel):
    description = StringField(required=True)
    name = StringField(required=True)
    catch_all = BooleanField(required=False, null=True)
    priority = IntField(required=False, null=True)

    meta = {"collection" : "okta_app_signon_policy"}

class PlatformInclude(EmbeddedDocument):
    os_expression = StringField(required=False)
    os_type = StringField(required=False)
    type = StringField(required=False)

class AppPolicySignOnRule(BaseEntityModel):
    name = StringField(required=True)
    policy_id = StringField(required=True)
    access = StringField(required=False, null=True)
    constraints = ListField(StringField(), required=False, null=True)
    custom_expression = StringField(required=False, null=True)
    device_assurances_included = ListField(StringField(), required=False, nul=True)
    device_is_managed = BooleanField(required=False, null=True)
    device_is_registered = BooleanField(required=False, null=True)
    factor_mode = StringField(required=False, nul=True)
    groups_excluded = ListField(StringField(), required=False, null =True)
    groups_included = ListField(StringField(), required=False, null=True)
    inactivity_period = StringField(required=False, null=True)
    network_connection = StringField(required=False, null=True)
    network_excludes = ListField(StringField(), required=False, null=True)
    network_includes = ListField(StringField(), required=False, null=True)
    platform_include = EmbeddedDocumentListField(PlatformInclude, required=False, null=True)
    priority = IntField(required=False, null=True)
    re_authentication_frequency = StringField(required=False, nul=True)
    risk_score = IntField(required=False, nul=True)
    status = StringField(required=False, null=True)
    type = StringField(required=False, null =True)
    user_types_excluded = ListField(StringField(), required=False, null= True)
    user_types_included = ListField(StringField(), required=False, null= True)
    users_excluded = ListField(StringField(), required=False, null=True)
    users_included = ListField(StringField(), required=False, null=True)
    
    meta = {"collection" : "okta_app_signon_policy_rule"}

class AppSAMLSettings(BaseEntityModel):
    app_id = StringField(required=True)
    settings = DictField(required=False, null=True)

    meta = {"collection" : "okta_app_saml_app_settings"}


class AppGroupAssignment(BaseEntityModel):
    app_id = StringField(required=True)
    group_id = StringField(required=True)
    priority = IntField(required=False)
    profile = DictField(required=False)
    retain_assignment = BooleanField(required=False)
    timeouts = EmbeddedDocumentListField(Timeouts, required=False)

    meta = {"collection" : "okta_app_group_assignment"}

class AppSharedCredentials(BaseEntityModel):
    label = StringField(required=True)
    accessibility_error_redirect_url = StringField(required=False, null=True)
    accessibility_login_redirect_url = StringField(required=False, null=True)
    accessibility_self_service = BooleanField(required=False, null=True)
    admin_note = StringField(required=False, null=True)
    app_links_json = StringField(required=False, null=True)
    auto_submit_toolbar = BooleanField(required=False, null=True)
    button_field = StringField(required=False, null=True)
    checkbox = StringField(required=False, null=True)
    enduser_note = StringField(required=False, null=True)
    hide_ios = BooleanField(required=False, null=True)
    hide_web = BooleanField(required=False, null=True)
    logo = StringField(required=False, null=True)
    password_field = StringField(required=False, null=True)
    preconfigured_app = StringField(required=False, null=True)
    redirect_url = StringField(required=False, null=True)
    shared_password = StringField(required=False, null=True)
    shared_username = StringField(required=False, null=True)
    status = StringField(required=False, null=True)
    timeouts = EmbeddedDocumentListField(Timeouts, required=False, null=True)
    url = StringField(required=False, null=True)
    url_regex = StringField(required=False, null=True)
    user_name_template = StringField(required=False, null=True)
    user_name_template_push_status = StringField(required=False, null=True)
    user_name_template_suffix = StringField(required=False, null=True)
    user_name_template_type = StringField(required=False, null=True)
    username_field = StringField(required=False, null=True)

    meta = {"collection" :"okta_app_shared_credentials"}

class AppBookMark(BaseEntityModel):
    label = StringField(required=True)
    url = StringField(required=True)
    accessibility_error_redirect_url = StringField(required=False, null=True)
    accessibility_login_redirect_url = StringField(required=False, null=True)
    accessibility_self_service = BooleanField(required=False, null=True)
    admin_note = StringField(required=False, null=True)
    app_links_json = StringField(required=False, null=True)
    authentication_policy = StringField(required=False, null=True)
    auto_submit_toolbar = BooleanField(required=False, null=True)
    enduser_note = StringField(required=False, null=True)
    hide_ios = BooleanField(required=False, null=True)
    hide_web = BooleanField(required=False, null=True)
    logo = StringField(required=False, null=True)
    request_integration = BooleanField(required=False, null=True)
    status = StringField(required=False, null=True)
    timeouts = EmbeddedDocumentListField(Timeouts, required=False, null=True)
    
    meta = {"collection" : "okta_app_bookmark"}

class AppAutoLogin(BaseEntityModel):
    label = StringField(required=True)
    accessibility_error_redirect_url = StringField(required=False, null=True)
    accessibility_login_redirect_url = StringField(required=False, null=True)
    accessibility_self_service = BooleanField(required=False, null=True)
    admin_note = StringField(required=False, null=True)
    app_links_json = StringField(required=False, null=True)
    app_settings_json = StringField(required=False, null=True)
    auto_submit_toolbar = BooleanField(required=False, null=True)
    credentials_scheme = StringField(required=False, null=True)
    enduser_note = StringField(required=False, null=True)
    hide_ios = BooleanField(required=False, null=True)
    hide_web = BooleanField(required=False, null=True)
    logo = StringField(required=False, null=True)
    preconfigured_app = StringField(required=False, null=True)
    reveal_password = BooleanField(required=False, null=True)
    shared_password = StringField(required=False, null=True)
    shared_username = StringField(required=False, null=True)
    sign_on_redirect_url = StringField(required=False, null=True)  
    sign_on_url = StringField(required=False, null=True)
    status = StringField(required=False, null=True)
    timeouts = EmbeddedDocumentListField(Timeouts, required=False, null=True)
    user_name_template = StringField(required=False, null=True)
    user_name_template_push_status = StringField(required=False, null=True)
    user_name_template_suffix = StringField(required=False, null=True)
    user_name_template_type = StringField(required=False, null=True)
    
    meta = {"collection": "okta_app_auto_login"}

class AppBasicAuth(BaseEntityModel):
    auth_url = StringField(required=True)
    label = StringField(required=True)
    url = StringField(required=True)
    accessibility_error_redirect_url = StringField(required=False, null=True)
    accessibility_login_redirect_url = StringField(required=False, null=True)
    accessibility_self_service = BooleanField(required=False, null=True)
    admin_note = StringField(required=False, null=True)
    app_links_json = StringField(required=False, null=True)
    auto_submit_toolbar = BooleanField(required=False, null=True)
    enduser_note = StringField(required=False, null=True)
    hide_ios = BooleanField(required=False, null=True)
    hide_web = BooleanField(required=False, null=True)
    logo = StringField(required=False, null=True)
    status = StringField(required=False, null=True)
    timeouts = EmbeddedDocumentListField(Timeouts, required=False, null=True)
    
    meta = {"collection": "okta_app_basic_auth"}

class AppSwa(BaseEntityModel):
    label = StringField(required=True)
    accessibility_error_redirect_url = StringField(null=True,required=False)
    accessibility_login_redirect_url = StringField(null=True,required=False)
    accessibility_self_service = StringField(null=True,required=False)
    admin_note = StringField(null=True,required=False)
    app_links_json = StringField(null=True,required=False)
    auto_submit_toolbar = BooleanField(null=True,required=False)
    button_field = StringField(null=True,required=False)
    checkbox = StringField(null=True,required=False)
    enduser_note = StringField(null=True,required=False)
    hide_ios = BooleanField(null=True,required=False)
    hide_web = BooleanField(null=True,required=False)
    logo = StringField(null=True,required=False)
    password_field = StringField(null=True,required=False)
    preconfigured_app = StringField(null=True,required=False)
    redirect_url = StringField(null=True,required=False)
    status = StringField(null=True,required=False)
    timeouts = EmbeddedDocumentListField(Timeouts, required=False)
    url = StringField(null=True,required=False)
    url_regex = StringField(null=True,required=False)
    user_name_template = StringField(null=True,required=False)
    user_name_template_push_status = StringField(null=True,required=False)
    user_name_template_suffix = StringField(null=True,required=False)
    user_name_template_type = StringField(null=True,required=False)
    username_field = StringField(null=True,required=False)
    
    meta = {"collection" : "okta_app_swa"}

class AppUser(BaseEntityModel):
    app_id = StringField(required=True)
    user_id = StringField(required=True)
    password = StringField(required=False, null=True)
    profile = DictField(required=False, null=True)
    retain_assignment = BooleanField(required=False, null=True)
    username = StringField(required=False, null=True)

    meta = {"collection" : "okta_app_user"}

class AppOauthApiScope(BaseEntityModel):
    app_id = StringField(required=True)
    issuer = StringField(required=True)
    scopes = ListField(StringField(), required=False)

    meta = {"collection" : "okta_app_oauth_api_scope"}

class AppOauthPostRedirectUri(BaseEntityModel):
    app_id = StringField(required=True)
    uri = StringField(required=True)

    meta = {"collection" : "okta_app_oauth_post_logout_redirect_uri"}

class AppOauthRedirectUri(BaseEntityModel):
    app_id = StringField(required=True)
    uri = StringField(required=True)
    
    meta = {"collection" : "okta_app_oauth_redirect_uri"}

class AppUserBaseSchemaProperty(BaseEntityModel):
    app_id = StringField(required=True)
    index = StringField(required=True)
    title = StringField(required=True)
    type = StringField(required=True)
    master = StringField(required=False, null=True)
    pattern = StringField(required=False, null=True)
    permissions = StringField(required=False, null=True)
    required = BooleanField(required=False, null=True)
    user_type = StringField(required=False, null=True)
    
    meta = {"collection": "okta_app_user_base_schema_property"}

class AppSecurePasswordStore(BaseEntityModel):
    label = StringField(required=True)
    password_field = StringField(required=True)
    url = StringField(required=True)
    username_field = StringField(required=True)
    accessibility_error_redirect_url = StringField(required=False, null=True)
    accessibility_login_redirect_url = StringField(required=False, null=True)
    accessibility_self_service = BooleanField(required=False, null=True)
    admin_note = StringField(required=False, null=True)
    app_links_json = StringField(required=False, null=True)
    auto_submit_toolbar = BooleanField(required=False, null=True)
    credentials_scheme = StringField(required=False, null=True)
    enduser_note = StringField(required=False, null=True)
    hide_ios = BooleanField(required=False, null=True)
    hide_web = BooleanField(required=False, null=True)
    logo = StringField(required=False, null=True)
    optional_field1 = StringField(required=False, null=True)
    optional_field1_value = StringField(required=False, null=True)
    optional_field2 = StringField(required=False, null=True)
    optional_field2_value = StringField(required=False, null=True)
    optional_field3 = StringField(required=False, null=True)
    optional_field3_value = StringField(required=False, null=True)
    reveal_password = BooleanField(required=False, null=True)
    shared_password = StringField(required=False, null=True)
    shared_username = StringField(required=False, null=True)
    status = StringField(required=False, null=True)
    timeouts = EmbeddedDocumentListField(Timeouts, required=False, null=True)
    user_name_template = StringField(required=False, null=True)
    user_name_template_push_status = StringField(required=False, null=True)
    user_name_template_suffix = StringField(required=False, null=True)
    user_name_template_type = StringField(required=False, null=True)
    
    meta = {"collection": "okta_app_secure_password_store"}
    
class AppThreeField(BaseEntityModel):
    label = StringField(required=True)
    url = StringField(required=True)
    username_selector = StringField(required=True)
    password_selector = StringField(required=True)
    extra_field_value = StringField(required=False, null=True)
    extra_field_selector = StringField(required=False, null=True)
    button_selector = StringField(required=False, null=True)
    accessibility_error_redirect_url = StringField(required=False, null=True)
    accessibility_login_redirect_url = StringField(required=False, null=True)
    accessibility_self_service = BooleanField(required=False, null=True)
    admin_note = StringField(required=False, null=True)
    app_links_json = StringField(required=False, null=True)
    auto_submit_toolbar = BooleanField(required=False, null=True)
    credentials_scheme = StringField(required=False, null=True)
    enduser_note = StringField(required=False, null=True)
    hide_ios = BooleanField(required=False, null=True)
    hide_web = BooleanField(required=False, null=True)
    logo = StringField(required=False, null=True)
    reveal_password = BooleanField(required=False, null=True)
    shared_password = StringField(required=False, null=True)
    shared_username = StringField(required=False, null=True)
    status = StringField(required=False, null=True)
    timeouts = EmbeddedDocumentListField(Timeouts, required=False, null=True)
    url_regex = StringField(required=False, null=True)
    user_name_template = StringField(required=False, null=True)
    user_name_template_push_status = StringField(required=False, null=True)
    user_name_template_suffix = StringField(required=False, null=True)
    user_name_template_type = StringField(required=False, null=True)
    
    meta = {"collection": "okta_app_three_field"}
    