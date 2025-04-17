from rest_framework import serializers


class EventHookSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    events = serializers.ListField(required=True)
    channel = serializers.DictField(required=True)
    auth = serializers.DictField(required=False)