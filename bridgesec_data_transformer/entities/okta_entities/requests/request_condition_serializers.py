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
    condition_id = serializers.CharField(max_length=255, required=True)
    resource_id = serializers.CharField(max_length=255, required=True)
    approval_sequence_id = serializers.CharField(max_length=255, required=False, allow_blank=True)
    name = serializers.CharField(max_length=255, required=True)
    status = serializers.CharField(max_length=50, required=False, allow_blank=True)
    priority = serializers.IntegerField(required=False)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    created = serializers.CharField(max_length=50, required=False, allow_blank=True)
    created_by = serializers.CharField(max_length=255, required=False, allow_blank=True)
    last_updated = serializers.CharField(max_length=50, required=False, allow_blank=True)
    last_updated_by = serializers.CharField(max_length=255, required=False, allow_blank=True)
    access_scope_settings = serializers.ListField(child=serializers.DictField(), required=False)
    requester_settings = serializers.ListField(child=serializers.DictField(), required=False)
    access_duration_settings = serializers.ListField(child=serializers.DictField(), required=False)


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
    request_id = serializers.CharField(required=True)
    requested = serializers.DictField(required=True)
    requested_for = serializers.DictField(required=True)
    requester_field_values = serializers.DictField(required=False)
    status = serializers.CharField(required=False, allow_blank=True)
    created = serializers.CharField(required=False, allow_blank=True)
    created_by = serializers.CharField(required=False, allow_blank=True)
    last_updated = serializers.CharField(required=False, allow_blank=True)
    last_updated_by = serializers.CharField(required=False, allow_blank=True)
    access_duration = serializers.CharField(required=False, allow_blank=True)
    granted = serializers.CharField(required=False, allow_blank=True)
    grant_status = serializers.CharField(required=False, allow_blank=True)
    resolved = serializers.CharField(required=False, allow_blank=True)
    revocation_scheduled = serializers.CharField(required=False, allow_blank=True)
    revocation_status = serializers.CharField(required=False, allow_blank=True)
    revoked = serializers.CharField(required=False, allow_blank=True)
