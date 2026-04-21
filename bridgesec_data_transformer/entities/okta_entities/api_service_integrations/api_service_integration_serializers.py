from rest_framework import serializers


class ApiServiceIntegrationSerializer(serializers.Serializer):
    api_service_integration_id = serializers.CharField(required=True)
    type = serializers.CharField(required=True)
    name = serializers.CharField(required=False, allow_blank=True)
    config_guide_url = serializers.CharField(required=False, allow_blank=True)
    created = serializers.CharField(required=False, allow_blank=True)
    created_at = serializers.CharField(required=False, allow_blank=True)
    granted_scopes = serializers.ListField(child=serializers.CharField(), required=False)
