from rest_framework import serializers


class UiSchemaSerializer(serializers.Serializer):
    ui_schema_id = serializers.CharField(required=True)
    created = serializers.CharField(required=False, allow_blank=True)
    last_updated = serializers.CharField(required=False, allow_blank=True)
    ui_schema = serializers.DictField(required=False)
