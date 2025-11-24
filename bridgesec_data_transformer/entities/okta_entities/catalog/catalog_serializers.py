from rest_framework import serializers


class CatalogEntryDefaultSerializer(serializers.Serializer):
    entry_id = serializers.CharField(max_length=255, required=True)


class CatalogEntryUserAccessRequestFieldsSerializer(serializers.Serializer):
    entry_id = serializers.CharField(max_length=255, required=True)
    user_id = serializers.CharField(max_length=255, required=True)


class EndUserMyRequestsSerializer(serializers.Serializer):
    entry_id = serializers.CharField(max_length=255, required=True)
    id = serializers.CharField(max_length=255, required=False)
    requester_field_values = serializers.ListField(child=serializers.DictField(), required=False)
