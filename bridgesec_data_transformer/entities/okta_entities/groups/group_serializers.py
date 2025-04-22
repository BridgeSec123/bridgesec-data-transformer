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

class GroupSchemaPropertySerializer(serializers.Serializer):
    index = serializers.CharField()
    title = serializers.CharField()
    type = serializers.CharField()
    array_enum = serializers.ListField(required=False)
    array_one_of = serializers.ListField(required=False)
    array_type = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    enum = serializers.ListField(required=False)
    external_name = serializers.CharField(required=False)
    external_namespace = serializers.CharField(required=False)
    master = serializers.CharField(required=False)
    master_override_priority = serializers.CharField(required=False)
    max_length = serializers.CharField(required=False)
    min_length = serializers.CharField(required=False)
    one_of = serializers.ListField(required=False)
    permissions = serializers.ListField(required=False)
    required = serializers.BooleanField(required=False)
    scope = serializers.CharField(required=False)
    unique = serializers.CharField(required=False)