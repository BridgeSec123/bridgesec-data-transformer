from rest_framework import serializers


class TranslationSerializer(serializers.Serializer):
    language = serializers.CharField()
    template = serializers.CharField()

class SmsTemplateSerializer(serializers.Serializer):
    type = serializers.CharField()
    template = serializers.CharField()
    translations = TranslationSerializer(many=True, required=False)