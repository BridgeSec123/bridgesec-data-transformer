from mongoengine import BooleanField, DictField, ListField, StringField

from entities.models.base import BaseEntityModel


class User(BaseEntityModel):
    email = StringField(null=True, required=True)
    first_name = StringField(required=True)
    last_name = StringField(required=True)
    mobile_phone = StringField(null=True, required=False)
    second_email  = StringField(null=True, required=False)
    login = StringField(null=True, required=False)
    
    meta = {"collection": "okta_user"}


class UserType(BaseEntityModel):
    name = StringField(required=True)
    description = StringField()
    display_name = StringField()
    
    meta = {"collection": "okta_user_type"}

class UserFactor(BaseEntityModel):
    provider_id = StringField(required=True)
    active = BooleanField(required=False, null=True)
    
    meta = {"collection": "okta_factor"}

class UserAdminRoles(BaseEntityModel):
    user_id = StringField(required=True)
    admin_roles = StringField(required=True)
    disable_notifications = BooleanField(required=False, null=True)
    
    meta = {"collection": "okta_user_admin_roles"}

class UserSchemaProperty(BaseEntityModel):
    index = StringField(required=True)
    title = StringField(required=True)
    type = StringField(required=True)
    description = StringField(required=False, null=True)
    master = StringField(required=False, null=True)
    scope = StringField(required=False, null=True)
    user_type = StringField(required=False, null=True)
    array_enum = ListField(StringField(), required=False, null=True)
    array_one_of = ListField(DictField(), required=False, null=True)
    array_type = StringField(required=False, null=True)
    enum = ListField(StringField(), required=False, null=True)
    external_name = StringField(required=False, null=True)
    external_namespace = StringField(required=False, null=True)
    master_override_priority = ListField(DictField(), required=False, null=True)
    max_length = StringField(required=False, null=True)
    min_length = StringField(required=False, null=True)
    one_of = ListField(DictField(), required=False, null=True)
    pattern = StringField(required=False, null=True)
    permissions = StringField(required=False, null=True)
    required = BooleanField(required=False, null=True)
    unique = StringField(required=False, null=True)
    
    meta = {"collection": "okta_user_schema_property"}

class AdminRoleTargets(BaseEntityModel):
    user_id = StringField(required=True)
    role_type = StringField(required=True)
    apps = ListField(StringField(), required=False, null=True)
    groups = ListField(StringField(), required=False, null=True)

    meta = {"collection": "okta_admin_role_targets"}

class RoleSubscription(BaseEntityModel):
    notification_type = StringField(required=True)
    role_type = StringField(required=True)
    status = StringField(required=False, null=True)

    meta = {"collection": "okta_role_subscription"}

class UserBaseSchemaProperty(BaseEntityModel):
    index = StringField(required=True)
    title = StringField(required=True)
    type = StringField(required=True)
    master = StringField(required=False, null=True)
    pattern = StringField(required=False, null=True)
    permissions = StringField(required=False, null=True)
    required = BooleanField(required=False, null=True)
    user_type = StringField(required=False, null=True)

    meta = {"collection": "okta_user_base_schema_property"}

class UserGroupMemberships(BaseEntityModel):
    user_id = StringField(required=True)
    groups = ListField(StringField(), required=True)

    meta = {"collection": "okta_user_group_memberships"}
