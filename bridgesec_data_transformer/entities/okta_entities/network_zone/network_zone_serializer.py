from rest_framework import serializers


class NetworkZoneSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    type = serializers.CharField(max_length=255)
    asns = serializers.ListField(child=serializers.CharField(max_length=255))
    dynamic_locations = serializers.ListField(child=serializers.CharField(max_length=255))
    dynamic_locations_excluded = serializers.ListField(child=serializers.CharField(max_length=255))
    dynamic_proxy_type = serializers.CharField(max_length=255)
    gateways = serializers.ListField(child=serializers.CharField(max_length=255))
    ip_service_categories_exclude = serializers.ListField(child=serializers.CharField(max_length=255))
    ip_service_categories_include = serializers.ListField(child=serializers.CharField(max_length=255))
    proxies = serializers.ListField(child=serializers.CharField(max_length=255))
    status = serializers.CharField(max_length=255)
    usage = serializers.CharField(max_length=255)