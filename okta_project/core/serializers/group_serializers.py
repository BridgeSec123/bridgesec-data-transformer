from rest_framework import serializers


class GroupSerializer(serializers.Serializer):
    name = serializers.CharField()
    description = serializers.CharField()
    