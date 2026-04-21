from rest_framework import serializers


class NetworkZoneSerializer(serializers.Serializer):
    network_id = serializers.CharField(max_length=255, required=False, allow_blank=True)
    name = serializers.CharField(max_length=255)
    type = serializers.CharField(max_length=255)
    asns = serializers.ListField(child=serializers.CharField(max_length=255), required=False, allow_null=True)
    dynamic_locations = serializers.ListField(child=serializers.CharField(max_length=255), required=False, allow_null=True)
    dynamic_locations_excluded = serializers.ListField(child=serializers.CharField(max_length=255), required=False, allow_null=True)
    dynamic_proxy_type = serializers.CharField(max_length=255, required=False, allow_null=True)
    gateways = serializers.ListField(child=serializers.CharField(max_length=255), required=False, allow_null=True)
    ip_service_categories_exclude = serializers.ListField(child=serializers.CharField(max_length=255), required=False, allow_null=True)
    ip_service_categories_include = serializers.ListField(child=serializers.CharField(max_length=255), required=False, allow_null=True)
    proxies = serializers.ListField(child=serializers.CharField(max_length=255), required=False, allow_null=True)
    status = serializers.CharField(max_length=255, required=False, allow_null=True)
    usage = serializers.CharField(max_length=255, required=False, allow_null=True)
    system = serializers.BooleanField(required=False, allow_null=True)
