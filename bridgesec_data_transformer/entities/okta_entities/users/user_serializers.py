from rest_framework import serializers


class UserSerializer(serializers.Serializer):
    email = serializers.CharField(required=True, allow_null=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    login = serializers.CharField(required=True, allow_null=True)
    city = serializers.CharField(required=False, allow_null=True)
    cost_center = serializers.CharField(required=False, allow_null=True)
    country_code = serializers.CharField(required=False, allow_null=True)
    custom_profile_properties = serializers.DictField(required=False, allow_null=True)
    custom_profile_properties_to_ignore = serializers.ListField(
        child=serializers.CharField(), required=False, allow_null=True
    )
    department = serializers.CharField(required=False, allow_null=True)
    display_name = serializers.CharField(required=False, allow_null=True)
    division = serializers.CharField(required=False, allow_null=True)
    employee_number = serializers.CharField(required=False, allow_null=True)
    expire_password_on_create = serializers.BooleanField(required=False, allow_null=True)
    honorofix_prefix = serializers.CharField(required=False, allow_null=True)
    honorofix_suffix = serializers.CharField(required=False, allow_null=True)
    locale = serializers.CharField(required=False, allow_null=True)
    manager = serializers.CharField(required=False, allow_null=True)
    manager_id = serializers.CharField(required=False, allow_null=True)
    middle_name = serializers.CharField(required=False, allow_null=True)
    mobile_phone = serializers.CharField(required=False, allow_null=True)
    nick_name = serializers.CharField(required=False, allow_null=True)
    old_password = serializers.CharField(required=False, allow_null=True)
    organization = serializers.CharField(required=False, allow_null=True)
    password = serializers.CharField(required=False, allow_null=True)
    password_inline_hook = serializers.CharField(required=False, allow_null=True)
    password_hash = serializers.ListField(child=serializers.CharField(), required=False)
    postal_address = serializers.CharField(required=False, allow_null=True)
    preferred_language = serializers.CharField(required=False, allow_null=True)
    primary_phone = serializers.CharField(required=False, allow_null=True)
    profile_url = serializers.CharField(required=False, allow_null=True)
    recovery_answer = serializers.CharField(required=False, allow_null=True)
    recovery_question = serializers.CharField(required=False, allow_null=True)
    second_email = serializers.CharField(required=False, allow_null=True)
    state = serializers.CharField(required=False, allow_null=True)
    status = serializers.CharField(required=False, allow_null=True)
    street_address = serializers.CharField(required=False, allow_null=True)
    timezone = serializers.CharField(required=False, allow_null=True)
    title = serializers.CharField(required=False, allow_null=True)
    user_type = serializers.CharField(required=False, allow_null=True)
    zip_code = serializers.CharField(required=False, allow_null=True)
    

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