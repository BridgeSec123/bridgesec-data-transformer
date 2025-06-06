from rest_framework import serializers


class UserSerializer(serializers.Serializer):
    email = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    login = serializers.CharField()
    mobile_phone = serializers.CharField(allow_null=True, required=False)
    second_email = serializers.CharField(allow_null=True, required=False)

    
    

class UserTypeSerializer(serializers.Serializer):
    name = serializers.CharField()
    displayName = serializers.CharField()
    description = serializers.CharField()

class UserFactorSerializer(serializers.Serializer):
    provider_id = serializers.CharField()
    active = serializers.BooleanField(allow_null=True, required=False)

class UserAdminRolesSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    admin_roles = serializers.CharField()
    disable_notifications = serializers.BooleanField(allow_null=True, required=False)

class UserSchemaPropertySerializer(serializers.Serializer):
    index = serializers.CharField()
    title = serializers.CharField()
    type = serializers.CharField()
    description = serializers.CharField(allow_null=True, required=False)
    master = serializers.CharField(allow_null=True, required=False)
    scope = serializers.CharField(allow_null=True, required=False)
    user_type = serializers.CharField(allow_null=True, required=False)
    array_enum = serializers.ListField(child=serializers.CharField(), allow_null=True, required=False)
    array_one_of = serializers.ListField(child=serializers.DictField(), allow_null=True, required=False)
    array_type = serializers.CharField(allow_null=True, required=False)
    enum = serializers.ListField(child=serializers.CharField(), allow_null=True, required=False)
    external_name = serializers.CharField(allow_null=True, required=False)
    external_namespace = serializers.CharField(allow_null=True, required=False)
    master_override_priority = serializers.ListField(child=serializers.DictField(), allow_null=True, required=False)
    max_length = serializers.CharField(allow_null=True, required=False)
    min_length = serializers.CharField(allow_null=True, required=False)
    one_of = serializers.ListField(child=serializers.DictField(), allow_null=True, required=False)
    pattern = serializers.CharField(allow_null=True, required=False)
    permissions = serializers.CharField(allow_null=True, required=False)
    required = serializers.BooleanField(allow_null=True, required=False)
    unique = serializers.CharField(allow_null=True, required=False)

class AdminRoleTargetsSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    role_type = serializers.CharField()
    apps = serializers.ListField(child=serializers.CharField(), allow_null=True, required=False)
    groups = serializers.ListField(child=serializers.CharField(), allow_null=True, required=False)

class RoleSubscriptionSerializer(serializers.Serializer):
    notification_type = serializers.CharField()
    role_type = serializers.CharField()
    status = serializers.CharField()

class UserBaseSchemaPropertySerializer(serializers.Serializer):
    index = serializers.CharField()
    title = serializers.CharField()
    type = serializers.CharField()
    description = serializers.CharField(allow_null=True, required=False)
    master = serializers.CharField(allow_null=True, required=False)
    permissions = serializers.CharField(allow_null=True, required=False)
    required = serializers.BooleanField(allow_null=True, required=False)
    user_type = serializers.CharField(allow_null=True, required=False)

class UserGroupMembershipsSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    groups = serializers.CharField()