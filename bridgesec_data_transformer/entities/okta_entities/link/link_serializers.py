from rest_framework import serializers

class OktaLinkDefinitionSerializer(serializers.Serializer):
    associated_description = serializers.CharField(max_length=255)
    associated_title = serializers.CharField(max_length=255)
    associated_name = serializers.CharField(max_length=255)
    primary_description = serializers.CharField(max_length=255)
    primary_title = serializers.CharField(max_length=255)
    primary_name = serializers.CharField(max_length=255)