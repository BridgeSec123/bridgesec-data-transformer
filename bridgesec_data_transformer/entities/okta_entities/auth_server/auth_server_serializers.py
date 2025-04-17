from rest_framework import serializers


class AuthorizationServerSerializer(serializers.Serializer):
    auth_server_id = serializers.CharField()
    audiences = serializers.ListField(child=serializers.CharField())
    description = serializers.CharField(required=False)
    name = serializers.CharField()
    credentials_rotation_mode = serializers.CharField(required=False)
    issuer_mode = serializers.CharField(required=False)
    status = serializers.CharField(required=False)

class AuthorizationServerClaimSerializer(serializers.Serializer):
    auth_server_id = serializers.CharField()
    claim_type = serializers.CharField()
    name = serializers.CharField()
    value = serializers.CharField()
    alway_include_in_token = serializers.BooleanField(required=False)
    group_filter_type = serializers.CharField(required=False)
    scopes = serializers.ListField(child=serializers.CharField(), required=False)
    status = serializers.CharField(required=False)
    value_type = serializers.CharField(required=False)

class AuthorizationServerClaimDefaultSerializer(serializers.Serializer):
    auth_server_id = serializers.CharField()
    name = serializers.CharField()
    value = serializers.CharField(required=False)
    always_include_in_token = serializers.BooleanField(required=False)

class AuthorizationServerDefaultSerializer(serializers.Serializer):
    audiences = serializers.ListField(child=serializers.CharField(), required=False)
    credentials_rotation_mode = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    issuer_mode = serializers.CharField(required=False)
    name = serializers.CharField(required=False)
    status = serializers.CharField(required=False)

class AuthorizationServerPolicySerializer(serializers.Serializer):
    auth_server_id = serializers.CharField()
    policy_id = serializers.CharField()
    name = serializers.CharField()
    client_whitelist = serializers.ListField(child=serializers.CharField())
    description = serializers.CharField()
    priority = serializers.IntegerField()
    status = serializers.CharField(required=False)

class AuthorizationServerPolicyRuleSerializer(serializers.Serializer):
    auth_server_id = serializers.CharField()
    grant_type_whitelist = serializers.ListField(child=serializers.CharField())
    policy_id = serializers.CharField()
    name = serializers.CharField()
    priority = serializers.IntegerField()
    access_token_lifetime_minutes = serializers.IntegerField(required=False)
    group_blacklist = serializers.ListField(child=serializers.CharField(), required=False)
    group_whitelist = serializers.ListField(child=serializers.CharField(), required=False)
    inline_hook_id = serializers.CharField(required=False)
    refresh_token_lifetime_minutes = serializers.IntegerField(required=False)
    refresh_token_window_minutes = serializers.IntegerField(required=False)
    scope_whitelist = serializers.ListField(child=serializers.CharField(), required=False)
    status = serializers.CharField(required=False)
    type = serializers.CharField(required=False)
    user_blacklist = serializers.ListField(child=serializers.CharField(), required=False)
    user_whitelist = serializers.ListField(child=serializers.CharField(), required=False)

class AuthorizationServerScopeSerializer(serializers.Serializer):
    auth_server_id = serializers.CharField()
    name = serializers.CharField()
    consent = serializers.CharField(required=False)
    default = serializers.BooleanField(required=False)
    display_name = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    metadata_publish = serializers.CharField(required=False)
    optional = serializers.BooleanField(required=False)

class AuthTrustedServerSerializer(serializers.Serializer):
    auth_server_id = serializers.CharField()
    trusted = serializers.ListField(child=serializers.CharField())