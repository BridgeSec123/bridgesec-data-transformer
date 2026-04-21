from rest_framework import serializers


class CatalogEntryDefaultSerializer(serializers.Serializer):
    entry_id = serializers.CharField(max_length=255, required=True)
    name = serializers.CharField(required=False, allow_blank=True)
    requestable = serializers.CharField(required=False, allow_blank=True)
    label = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    parent = serializers.CharField(required=False, allow_blank=True)
    counts = serializers.DictField(required=False)


class CatalogEntryUserAccessRequestFieldsSerializer(serializers.Serializer):
    entry_id = serializers.CharField(max_length=255, required=True)
    field_id = serializers.CharField(required=False, allow_blank=True)
    required = serializers.CharField(required=False, allow_blank=True)
    type = serializers.CharField(required=False, allow_blank=True)
    label = serializers.CharField(required=False, allow_blank=True)
    maximum_value = serializers.CharField(required=False, allow_blank=True)
    read_only = serializers.CharField(required=False, allow_blank=True)
    value = serializers.CharField(required=False, allow_blank=True)
    choices = serializers.ListField(child=serializers.CharField(), required=False)


class EndUserMyRequestsSerializer(serializers.Serializer):
    request_id = serializers.CharField(required=False, allow_blank=True)
    entry_id = serializers.CharField(max_length=255, required=True)
    status = serializers.CharField(required=False, allow_blank=True)
    requester_field_values = serializers.ListField(child=serializers.DictField(), required=False)
