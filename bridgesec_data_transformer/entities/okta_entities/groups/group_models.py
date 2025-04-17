from mongoengine import DictField, StringField, ListField, BooleanField

from entities.models.base import BaseEntityModel


class Group(BaseEntityModel):
    name = StringField()
    description = StringField()
    custom_profile_attributes = DictField(null = True, required=False)

    meta = {"collection": "groups"}

class GroupMember(BaseEntityModel):
    group_id = StringField()
    users = ListField()
    
    meta = {"collection": "group_members"}

class GroupOwner(BaseEntityModel):
    group_id = StringField()
    id_of_group_owner = StringField()
    type = StringField()
    
    meta = {"collection": "group_owners"}

class GroupRole(BaseEntityModel):
    group_id = StringField()
    role_type = StringField()
    disable_notifications = BooleanField(required=False)
    resource_set_id = StringField(required=False)
    role_id = StringField(required=False)
    target_app_list = ListField(required=False)
    target_group_list = ListField(required=False)
    
    meta = {"collection": "group_roles"}

class GroupRule(BaseEntityModel):
    name = StringField()
    status = StringField(required=False)
    group_assignments = ListField()
    expression_type = StringField(required=False)
    expression_value = StringField()
    remove_assigned_users = BooleanField(required=False)
    users_excluded = ListField(required=False)
    
    meta = {"collection": "group_rules"}