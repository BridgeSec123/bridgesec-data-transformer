from rest_framework import status, viewsets
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from core.serializers.user_serializer import UserCreateSerializer
from core.utils.jwt_utils import generate_jwt_token

class UserCreateView(viewsets.ViewSet):
    @swagger_auto_schema(
        request_body=UserCreateSerializer,
        operation_description="Create a new user account",
        responses={201: "User created successfully", 400: "Invalid input"}
    )
    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token = generate_jwt_token(user)
            return Response(
                {"detail": "User created successfully", "token": token},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST) 