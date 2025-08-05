from mongoengine import BooleanField, IntField, ListField, StringField

from entities.models.base import BaseEntityModel


class AuthorizationServer(BaseEntityModel):
    auth_server_id = StringField()
    audiences = ListField()
    description = StringField(null=True,required=False)
    name = StringField()
    credentials_rotation_mode = StringField(null=True,required=False)
    issuer_mode = StringField(null=True,required=False)
    status = StringField(null=True,required=False)
    
    meta = {"collection" : "okta_auth_server"}

class AuthorizationServerClaim(BaseEntityModel):
    auth_server_id = StringField()
    claim_type = StringField()
    name = StringField()
    value = StringField()
    always_include_in_token = BooleanField(null=True, required=False)
    group_filter_type = StringField(null=True, required=False)
    scopes = ListField(null=True, required=False)
    status = StringField(null=True, required=False)
    value_type = StringField(null=True, required=False)
    
    meta = {"collection" : "okta_auth_server_claim"}

class AuthorizationServerClaimDefault(BaseEntityModel):
    auth_server_id = StringField()
    name = StringField()
    value = StringField(null=True, required=False)
    always_include_in_token = BooleanField(null=True, required=False)
    
    meta = {"collection" : "okta_auth_server_claim_default"}

class AuthorizationServerDefault(BaseEntityModel):
    audiences = ListField(null=True, required=False)
    credentials_rotation_mode = StringField(null=True, required=False)
    description = StringField(null=True, required=False)
    issuer_mode = StringField(null=True, required=False)
    name = StringField(null=True, required=False)
    status = StringField(null=True, required=False)
    
    meta = {"collection" : "okta_auth_server_default"}

class AuthorizationServerPolicy(BaseEntityModel):
    policy_id = StringField()
    auth_server_id = StringField()
    name = StringField()
    client_whitelist = ListField()
    description = StringField()
    priority = IntField()
    status = StringField(null=True, required=False)
    
    meta = {"collection" : "okta_auth_server_policy"}

class AuthorizationServerPolicyRule(BaseEntityModel):
    auth_server_id = StringField()
    grant_type_whitelist = ListField()
    policy_id = StringField()
    name = StringField()
    priority = IntField()
    access_token_lifetime_minutes = IntField(null=True, required=False)
    group_blacklist = ListField(null=True, required=False)
    group_whitelist = ListField(null=True, required=False)
    inline_hook_id = StringField(null=True, required=False)
    refresh_token_lifetime_minutes = IntField(null=True, required=False)
    refresh_token_window_minutes = IntField(null=True, required=False)
    scope_whitelist = ListField(null=True, required=False)
    status = StringField(null=True, required=False)
    type = StringField(null=True, required=False)
    user_blacklist = ListField(null=True, required=False)
    user_whitelist = ListField(null=True, required=False)
    
    meta = {"collection" : "okta_auth_server_policy_rule"}

class AuthorizationServerScope(BaseEntityModel):
    auth_server_id = StringField()
    name = StringField()
    consent = StringField(null=True, required=False)
    default = BooleanField(null=True, required=False)
    display_name = StringField(null=True, required=False)
    description = StringField(null=True, required=False)
    metadata_publish = StringField(null=True, required=False)
    optional = BooleanField(null=True, required=False)
    
    meta = {"collection" : "okta_auth_server_scope"}

class AuthTrustedServer(BaseEntityModel):
    auth_server_id = StringField()
    trusted = ListField()
    
    meta = {"collection" : "okta_trusted_server"}