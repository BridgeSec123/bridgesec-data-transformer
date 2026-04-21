from rest_framework import serializers


class EntitlementBundleSerializer(serializers.Serializer):
    bundle_id = serializers.CharField(required=True)
    name = serializers.CharField(max_length=255, required=True)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    target_resource_orn = serializers.CharField(max_length=255, required=False, allow_blank=True)
    status = serializers.CharField(max_length=50, required=False, allow_blank=True)
    target = serializers.DictField(required=False)
    entitlements = serializers.ListField(child=serializers.DictField(), required=False)
    created = serializers.CharField(required=False, allow_blank=True)
    last_updated = serializers.CharField(required=False, allow_blank=True)
    created_by = serializers.CharField(required=False, allow_blank=True)
    last_updated_by = serializers.CharField(required=False, allow_blank=True)


class PrincipalEntitlementSerializer(serializers.Serializer):
    entitlement_id = serializers.CharField(required=True)
    name = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    data_type = serializers.CharField(required=False, allow_blank=True)
    multi_value = serializers.BooleanField(required=False)
    required = serializers.BooleanField(required=False)
    external_value = serializers.CharField(required=False, allow_blank=True)
    parent_resource_orn = serializers.CharField(required=False, allow_blank=True)
    target_principal_orn = serializers.CharField(required=False, allow_blank=True)
    parent = serializers.DictField(required=False)
    target_principal = serializers.DictField(required=False)
    values = serializers.ListField(child=serializers.DictField(), required=False)


class ValuesSerializer(serializers.Serializer):
    external_value = serializers.CharField(max_length=500, required=True)
    name = serializers.CharField(max_length=255, required=True)


class EntitlementSerializer(serializers.Serializer):
    data_type = serializers.CharField(max_length=50, required=True)
    external_value = serializers.CharField(max_length=500, required=True)
    multi_value = serializers.BooleanField(required=True)
    name = serializers.CharField(max_length=255, required=True)
    parent = serializers.DictField(required=True)
    values = serializers.ListField(child=ValuesSerializer(), required=True)
    description = serializers.CharField(max_length=1000, required=False)
