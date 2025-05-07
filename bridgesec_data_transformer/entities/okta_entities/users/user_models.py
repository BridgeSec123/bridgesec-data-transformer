from mongoengine import BooleanField, EmailField, StringField, ListField, DictField

from entities.models.base import BaseEntityModel


class User(BaseEntityModel):
    user_id = StringField()
    firstName = StringField()
    lastName = StringField()
    mobilePhone = StringField(null=True, required=False)
    secondEmail = StringField(null=True, required=False)
    login = StringField()
    email = EmailField()
    
    meta = {"collection": "okta_user"}


class UserType(BaseEntityModel):
    name = StringField(required=True)
    description = StringField()
    displayName = StringField()
    
    meta = {"collection": "okta_user_type"}

class UserFactor(BaseEntityModel):
    provider_id = StringField(required=True)
    active = BooleanField(required=False)
    
    meta = {"collection": "okta_factor"}

class UserAdminRoles(BaseEntityModel):
    user_id = StringField(required=True)
    admin_roles = StringField(required=True)
    disable_notifications = BooleanField(required=False)
    
    meta = {"collection": "okta_user_admin_roles"}

class UserSchemaProperty(BaseEntityModel):
    index = StringField(required=True)
    title = StringField(required=True)
    type = StringField(required=True)
    description = StringField(required=False)
    master = StringField(required=False)
    scope = StringField(required=False)
    user_type = StringField(required=False)
    array_enum = ListField(StringField(), required=False)
    array_one_of = ListField(DictField(), required=False)
    array_type = StringField(required=False)
    enum = ListField(StringField(), required=False)
    external_name = StringField(required=False)
    external_namespace = StringField(required=False)
    master_override_priority = ListField(DictField(), required=False)
    max_length = StringField(required=False)
    min_length = StringField(required=False)
    one_of = ListField(DictField(), required=False)
    pattern = StringField(required=False)
    permissions = StringField(required=False)
    required = BooleanField(required=False)
    unique = StringField(required=False)
    
    meta = {"collection": "okta_user_schema_property"}

class AdminRoleTargets(BaseEntityModel):
    user_id = StringField(required=True)
    role_type = StringField(required=True)
    apps = ListField(StringField(), required=False)
    groups = ListField(StringField(), required=False)

    meta = {"collection": "okta_admin_role_targets"}

class RoleSubscription(BaseEntityModel):
    notification_type = StringField(required=True)
    role_type = StringField(required=True)
    status = StringField(required=False)

    meta = {"collection": "okta_role_subscription"}

class UserBaseSchemaProperty(BaseEntityModel):
    index = StringField(required=True)
    title = StringField(required=True)
    type = StringField(required=True)
    master = StringField(required=False)
    pattern = StringField(required=False)
    permissions = StringField(required=False)
    required = BooleanField(required=False)
    user_type = StringField(required=False)

    meta = {"collection": "okta_user_base_schema_property"}

class UserGroupMemberships(BaseEntityModel):
    user_id = StringField(required=True)
    groups = ListField(StringField(), required=True)

    meta = {"collection": "okta_user_group_memberships"}


