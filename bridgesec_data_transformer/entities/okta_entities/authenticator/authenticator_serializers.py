from rest_framework import serializers


class AuthenticatorSerializer(serializers.Serializer):
    key = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=255)
    status = serializers.CharField(required=False, max_length=255)
    legacy_ignore_name = serializers.BooleanField(required=False)
    provider_auth_port = serializers.IntegerField(required=False)
    provider_host = serializers.CharField(required=False, max_length=255)
    provider_hostname = serializers.CharField(required=False, max_length=255)
    provider_integration_key = serializers.CharField(required=False, max_length=255)
    provider_json = serializers.CharField(required=False, max_length=255)
    provider_secret_key = serializers.CharField(required=False, max_length=255)
    provider_shared_secret = serializers.CharField(required=False, max_length=255)
    provider_user_name_template = serializers.CharField(required=False, max_length=255)
    settings = serializers.CharField(required=False, max_length=255)