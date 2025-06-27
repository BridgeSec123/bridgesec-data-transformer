from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


class CustomTokenObtainPairView(TokenObtainPairView):
    @swagger_auto_schema(
        operation_description="Obtain a new JWT token by providing valid user credentials",
        responses={200: openapi.Response('Token pair obtained')}
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class CustomTokenRefreshView(TokenRefreshView):
    @swagger_auto_schema(
        operation_description="Refresh your JWT token using a valid refresh token",
        responses={200: openapi.Response('Token refreshed')}
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)