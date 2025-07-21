# serializers.py
from rest_framework import serializers

class RestoreDataSerializer(serializers.Serializer):
    data = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False
    )
