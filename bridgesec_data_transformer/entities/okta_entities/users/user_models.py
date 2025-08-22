from mongoengine import BooleanField, DictField, ListField, StringField, EmbeddedDocument, EmbeddedDocumentListField

from entities.models.base import BaseEntityModel
 
class PasswordHash(EmbeddedDocument):
    algorithm = StringField(required=True)
    hash = StringField(required=True)
    salt = StringField(required= False)
    salt_order = StringField(required=False)
    work_factor = StringField(required=False)

class User(BaseEntityModel):
    email = StringField(null=True, required=True)
    first_name = StringField(required=True)
    last_name = StringField(required=True)
    login = StringField(null=True, required=True)
    city = StringField(null=True, required=False)
    cost_center = StringField(null=True, required=False)
    country_code = StringField(null=True, required=False)
    custom_profile_properties = DictField(null=True, required=False)
    custom_profile_properties_to_ignore = ListField(StringField(), null=True, required=False)
    department = StringField(null=True, required=False)
    display_name = StringField(null=True, required=False)
    division = StringField(null=True, required=False)
    employee_number = StringField(null=True, required=False)
    expire_password_on_create = BooleanField(null=True, required=False)
    honorofix_prefix = StringField(null=True, required=False)
    honorofix_suffix = StringField(null=True, required=False)
    locale = StringField(null=True, required=False)
    manager = StringField(null=True, required=False)
    manager_id = StringField(null=True, required=False)
    middle_name = StringField(null=True, required=False)
    mobile_phone = StringField(null=True, required=False)
    nick_name = StringField(null=True, required=False)
    old_password = StringField(null=True, required=False)
    organization = StringField(null=True, required=False)
    password = StringField(null=True, required=False)
    password_inline_hook = StringField(null=True, required=False)
    password_hash =  EmbeddedDocumentListField(PasswordHash, required=False)
    postal_address = StringField(null=True, required=False)
    preferred_language = StringField(null=True, required=False)
    primary_phone = StringField(null=True, required=False)
    profile_url = StringField(null=True, required=False)
    recovery_answer = StringField(null=True, required=False)
    recovery_question = StringField(null=True, required=False)
    second_email = StringField(null=True, required=False)
    state = StringField(null=True, required=False)
    status = StringField(null=True, required=False)
    street_address = StringField(null=True, required=False)
    timezone = StringField(null=True, required=False)
    title = StringField(null=True, required=False)
    user_type = StringField(null=True, required=False)
    zip_code = StringField(null=True, required=False)
  
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
