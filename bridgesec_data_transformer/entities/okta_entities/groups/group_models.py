from mongoengine import BooleanField, DictField, ListField, StringField

from entities.models.base import BaseEntityModel


class Group(BaseEntityModel):
    group_id = StringField()
    name = StringField()
    description = StringField()
    custom_profile_attributes = DictField(null = True, required=False)

    meta = {"collection": "okta_group"}

class GroupMember(BaseEntityModel):
    group_id = StringField()
    users = ListField()
    
    meta = {"collection": "okta_group_memberships"} 

class GroupOwner(BaseEntityModel):
    group_id = StringField()
    id_of_group_owner = StringField()
    type = StringField()
    
    meta = {"collection": "okta_group_owner"}

class GroupRole(BaseEntityModel):
    group_id = StringField()
    role_type = StringField()
    disable_notifications = BooleanField(required=False)
    resource_set_id = StringField(required=False)
    role_id = StringField(required=False)
    target_app_list = ListField(required=False)
    target_group_list = ListField(required=False)
    
    meta = {"collection": "okta_group_role"}

class GroupRule(BaseEntityModel):
    name = StringField()
    status = StringField(required=False)
    group_assignments = ListField()
    expression_type = StringField(required=False)
    expression_value = StringField()
    remove_assigned_users = BooleanField(required=False)
    users_excluded = ListField(required=False)
    
    meta = {"collection": "okta_group_rule"}

class GroupSchemaProperty(BaseEntityModel):
    index = StringField()
    title = StringField()
    type = StringField()
    array_enum = ListField(required=False)
    array_one_of = ListField(required=False)
    array_type = StringField(required=False)
    description = StringField(required=False)
    enum = ListField(required=False)
    external_name = StringField(required=False)
    external_namespace = StringField(required=False)
    master = StringField(required=False)
    master_override_priority = StringField(required=False)
    max_length = StringField(required=False)
    min_length = StringField(required=False)
    one_of = ListField(required=False)
    permissions = ListField(required=False)
    required = BooleanField(required=False)
    scope = StringField(required=False)
    unique = StringField(required=False)
    
    meta = {"collection": "okta_group_schema_property"}