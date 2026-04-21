from rest_framework import serializers


class ApiTokenSerializer(serializers.Serializer):
    token_id = serializers.CharField(required=True)
    name = serializers.CharField(required=False, allow_blank=True)
    client_name = serializers.CharField(required=False, allow_blank=True)
    created = serializers.CharField(required=False, allow_blank=True)
    user_id = serializers.CharField(required=False, allow_blank=True)
    network = serializers.DictField(required=False)
