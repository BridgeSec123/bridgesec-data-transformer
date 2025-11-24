from rest_framework import serializers


class TargetSerializer(serializers.Serializer):
    external_id = serializers.CharField(max_length=255, required=True)
    type = serializers.CharField(max_length=100, required=True)


class EntitlementNestedSerializer(serializers.Serializer):
    id = serializers.CharField(max_length=255, required=True)
    values = serializers.ListField(required=True)


class ParentSerializer(serializers.Serializer):
    external_id = serializers.CharField(max_length=255, required=True)
    type = serializers.CharField(max_length=100, required=True)


class TargetPrincipalSerializer(serializers.Serializer):
    external_id = serializers.CharField(max_length=255, required=True)
    type = serializers.CharField(max_length=100, required=True)


class EntitlementBundleSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=True)
    target = TargetSerializer(required=True)
    entitlements = serializers.ListField(child=EntitlementNestedSerializer(), required=True)
    description = serializers.CharField(max_length=500, required=False)
    target_resource_orn = serializers.CharField(max_length=255, required=False)
    status = serializers.CharField(max_length=50, required=False)


class PrincipalEntitlementSerializer(serializers.Serializer):
    parent = ParentSerializer(required=True)
    target_principal = TargetPrincipalSerializer(required=True)


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
