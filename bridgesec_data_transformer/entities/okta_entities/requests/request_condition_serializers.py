from rest_framework import serializers


class AccessScopeSettingsSerializer(serializers.Serializer):
    type = serializers.CharField(max_length=100, required=True)
    id = serializers.ListField(child=serializers.CharField(), required=True)


class RequesterSettingsSerializer(serializers.Serializer):
    type = serializers.CharField(max_length=100, required=True)
    id = serializers.ListField(child=serializers.CharField(), required=True)


class AccessDurationSettingsSerializer(serializers.Serializer):
    type = serializers.CharField(max_length=100, required=True)
    duration = serializers.CharField(max_length=100, required=True)


class RequestConditionSerializer(serializers.Serializer):
    resource_id = serializers.CharField(max_length=255, required=True)
    approval_sequence_id = serializers.CharField(max_length=255, required=True)
    name = serializers.CharField(max_length=255, required=True)
    access_scope_settings = serializers.ListField(child=AccessScopeSettingsSerializer(), required=True)
    requester_settings = serializers.ListField(child=RequesterSettingsSerializer(), required=True)
    description = serializers.CharField(max_length=500, required=False)
    priority = serializers.IntegerField(required=False)
    access_duration_settings = serializers.ListField(child=AccessDurationSettingsSerializer(), required=False)


class RequestSequenceSerializer(serializers.Serializer):
    resource_id = serializers.CharField(max_length=255, required=True)
    sequence_id = serializers.CharField(max_length=24, min_length=24, required=True)


class RequestSettingsSerializer(serializers.Serializer):
    resource_id = serializers.CharField(max_length=255, required=True)


class RequestedSerializer(serializers.Serializer):
    entry_id = serializers.CharField(max_length=255, required=True)
    type = serializers.CharField(max_length=100, required=True)
    access_scope_id = serializers.CharField(max_length=255, required=False)
    access_scope_type = serializers.CharField(max_length=100, required=False)
    resource_id = serializers.CharField(max_length=255, required=False)
    resource_type = serializers.CharField(max_length=100, required=False)


class RequestedForSerializer(serializers.Serializer):
    external_id = serializers.CharField(max_length=255, required=True)
    type = serializers.CharField(max_length=100, required=True)


class RequesterFieldValuesSerializer(serializers.Serializer):
    id = serializers.CharField(max_length=255, required=False)
    label = serializers.CharField(max_length=500, required=False)
    type = serializers.CharField(max_length=100, required=False)
    value = serializers.CharField(max_length=500, required=False)
    values = serializers.ListField(child=serializers.CharField(), required=False)


class RequestTypeSerializer(serializers.Serializer):
    requested = RequestedSerializer(required=True)
    requested_for = RequestedForSerializer(required=True)
    requester_field_values = RequesterFieldValuesSerializer(required=False)
