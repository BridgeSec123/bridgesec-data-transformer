from rest_framework import serializers


class InlineHookSerializer(serializers.Serializer):
    name = serializers.CharField()
    version = serializers.CharField()
    type = serializers.CharField()
    channel_json = serializers.DictField(required=False)
    channel = serializers.DictField(required=False)
    status = serializers.CharField(required=False)
    auth = serializers.DictField(required=False)