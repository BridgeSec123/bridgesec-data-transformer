from rest_framework import serializers


class UserSerializer(serializers.Serializer):
    firstName = serializers.CharField()
    lastName = serializers.CharField()
    mobilePhone = serializers.CharField(allow_null=True, required=False)
    secondEmail = serializers.EmailField(allow_null=True, required=False)
    login = serializers.EmailField()
    email = serializers.EmailField()
