from rest_framework import serializers
from core.models.user import User
from django.contrib.auth.hashers import make_password

class UserCreateSerializer(serializers.Serializer):
    username = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if User.objects(username=attrs['username']).first():
            raise serializers.ValidationError({"username": "Username already exists"})

        if User.objects(email=attrs['email']).first():
            raise serializers.ValidationError({"email": "Email already exists"})
        
        return attrs

    def create(self, validated_data):
        hashed_password = make_password(validated_data["password"])
        user = User(
            username=validated_data['username'],
            email=validated_data["email"],
            password=hashed_password,
            role="user"
        )
        user.save()
        return user


