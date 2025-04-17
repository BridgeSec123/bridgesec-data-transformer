from rest_framework import serializers


class GroupSerializer(serializers.Serializer):
    name = serializers.CharField()
    description = serializers.CharField()
    custom_profile_attributes = serializers.DictField(required=False)


class GroupMemberSerializer(serializers.Serializer):
    group_id = serializers.CharField()
    users = serializers.ListField()
    
class GroupOwnerSerializer(serializers.Serializer):
    group_id = serializers.CharField()
    id_of_group_owner = serializers.CharField()
    type = serializers.CharField()
    
class GroupRoleSerializer(serializers.Serializer):
    group_id = serializers.CharField()
    role_type = serializers.CharField()
    disable_notifications = serializers.BooleanField(required=False)
    resource_set_id = serializers.CharField(required=False)
    role_id = serializers.CharField(required=False)
    target_app_list = serializers.ListField(required=False)
    target_group_list = serializers.ListField(required=False)
    
class GroupRuleSerializer(serializers.Serializer):
    name = serializers.CharField()
    status = serializers.CharField(required=False)
    group_assignments = serializers.ListField()
    expression_type = serializers.CharField(required=False)
    expression_value = serializers.CharField()
    remove_assigned_users = serializers.BooleanField(required=False)
    users_excluded = serializers.ListField(required=False)