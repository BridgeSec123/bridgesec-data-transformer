from rest_framework import serializers


class PushProviderSerializer(serializers.Serializer):
    push_provider_id = serializers.CharField(required=True)
    name = serializers.CharField(required=True)
    provider_type = serializers.CharField(required=True)
    last_updated_date = serializers.CharField(required=False, allow_blank=True)
    configuration = serializers.DictField(required=False)
