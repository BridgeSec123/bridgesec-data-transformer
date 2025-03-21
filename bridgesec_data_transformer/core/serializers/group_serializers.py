from rest_framework import serializers


class GroupSerializer(serializers.Serializer):
    name = serializers.CharField()
    description = serializers.CharField()
    custom_profile_attributes = serializers.DictField(required=False)