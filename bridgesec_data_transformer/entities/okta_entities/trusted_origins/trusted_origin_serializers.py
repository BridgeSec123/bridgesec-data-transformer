from rest_framework import serializers


class TrustedOriginSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    origin = serializers.CharField(required=True)
    scopes = serializers.ListField(child=serializers.CharField(), required=True)
    active = serializers.BooleanField(required=False)