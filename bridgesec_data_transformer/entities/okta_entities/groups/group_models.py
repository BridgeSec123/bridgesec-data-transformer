from mongoengine import BooleanField, DictField, ListField, StringField, IntField

from entities.models.base import BaseEntityModel


class Group(BaseEntityModel):
    group_id = StringField(required=True)
    name = StringField(required=True)
    description = StringField(required=False, null=True)
    custom_profile_attributes = DictField(null = True, required=False)

    meta = {"collection": "okta_group"}

class GroupMember(BaseEntityModel):
    group_id = StringField(required=True)
    users = ListField(required=True)
    
    meta = {"collection": "okta_group_memberships"} 

class GroupOwner(BaseEntityModel):
    group_id = StringField()
    id_of_group_owner = StringField()
    type = StringField()
    
    meta = {"collection": "okta_group_owner"}

class GroupRole(BaseEntityModel):
    group_id = StringField(required=True)
    role_type = StringField(required=True)
    disable_notifications = BooleanField(required=False, null=True)
    resource_set_id = StringField(required=False, null=True)
    role_id = StringField(required=False, null=True)
    target_app_list = ListField(required=False, null=True)
    target_group_list = ListField(required=False, null=True)
    
    meta = {"collection": "okta_group_role"}

class GroupRule(BaseEntityModel):
    name = StringField(required=True)
    expression_value = StringField(required=True)
    group_assignments = ListField(required=True)
    status = StringField(required=False, null=True)
    expression_type = StringField(required=False, null=True)
    remove_assigned_users = BooleanField(required=False, null=True)
    users_excluded = ListField(required=False, null=True)
    
    meta = {"collection": "okta_group_rule"}

class GroupSchemaProperty(BaseEntityModel):
    index = StringField(required=True)
    title = StringField(required=True)
    type = StringField(required=True)
    array_enum = ListField(required=False, null=True)
    array_one_of = ListField(required=False, null=True)
    array_type = StringField(required=False, null=True)
    description = StringField(required=False, null=True)
    enum = ListField(required=False, null=True)
    external_name = StringField(required=False, null=True)
    external_namespace = StringField(required=False, null=True)
    master = StringField(required=False, null=True)
    master_override_priority = StringField(required=False, null=True)
    max_length = IntField(required=False, null=True)
    min_length = IntField(required=False, null=True)
    one_of = ListField(required=False, null=True)
    permissions = ListField(required=False, null=True)
    required = BooleanField(required=False, null=True)
    scope = StringField(required=False, null=True)
    unique = StringField(required=False, null=True)
    
    meta = {"collection": "okta_group_schema_property"}