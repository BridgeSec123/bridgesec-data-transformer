from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from core.serializers.login_serializer import UserLoginSerializer
from core.utils.jwt_utils import generate_jwt_token

class CustomTokenObtainPairView(TokenObtainPairView):
    # @swagger_auto_schema(
    #     operation_description="Obtain a new JWT token by providing valid user credentials",
    #     responses={200: openapi.Response('Token pair obtained')}
    # )
    # def post(self, request, *args, **kwargs):
    #     return super().post(request, *args, **kwargs)
    @swagger_auto_schema(
        request_body=UserLoginSerializer,
        operation_description="Login and get JWT token",
        responses={200: "JWT Token returned"}
    )
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]
            token = generate_jwt_token(user)
            return Response({"token": token}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenRefreshView(TokenRefreshView):
    @swagger_auto_schema(
        operation_description="Refresh your JWT token using a valid refresh token",
        responses={200: openapi.Response('Token refreshed')},
        tags=["login"]
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
    

class CustomTokenObtainView(APIView):
    @swagger_auto_schema(
        request_body=UserLoginSerializer,
        operation_description="Login and get JWT token",
        responses={200: "JWT Token returned"},
        tags=["login"]
    )
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]
            
            #  Generate a JWT with user_id, email, role, exp
            token = generate_jwt_token(user)
            
            # Return token to frontend
            return Response({"token": token}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)