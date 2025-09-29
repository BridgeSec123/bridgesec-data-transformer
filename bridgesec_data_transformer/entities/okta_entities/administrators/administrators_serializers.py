from rest_framework import serializers

class AdminRoleCustomSerializer(serializers.Serializer):
    custom_role_id = serializers.CharField(max_length=255)
    description = serializers.CharField(max_length=255)
    label = serializers.CharField(max_length=255)
    permissions = serializers.ListField(child=serializers.CharField(max_length=255))

class AdminResourceSetSerializer(serializers.Serializer):
    description = serializers.CharField(max_length=255)
    label = serializers.CharField(max_length=255)
    resources = serializers.ListField(child=serializers.CharField(max_length=255))