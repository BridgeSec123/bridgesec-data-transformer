from rest_framework import serializers


class DomainSerializer(serializers.Serializer):
    domain_id = serializers.CharField(required=True)
    name = serializers.CharField(required=False, allow_blank=True)
    brand_id = serializers.CharField(required=False, allow_blank=True)
    certificate_source_type = serializers.CharField(required=False, allow_blank=True)
    validation_status = serializers.CharField(required=False, allow_blank=True)
    dns_records = serializers.ListField(child=serializers.DictField(), required=False)
    public_certificate = serializers.DictField(required=False)
