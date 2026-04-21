from rest_framework import serializers


class HookKeySerializer(serializers.Serializer):
    hook_key_id = serializers.CharField(required=True)
    name = serializers.CharField(required=True)
    key_id = serializers.CharField(required=False, allow_blank=True)
    created = serializers.CharField(required=False, allow_blank=True)
    is_used = serializers.BooleanField(required=False)
    last_updated = serializers.CharField(required=False, allow_blank=True)
