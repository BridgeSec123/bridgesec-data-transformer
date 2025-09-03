from django.contrib import admin
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

from core.views.okta_logout_viewset import OktaLogoutView
from core.views.user_views import UserCreateView
from core.views.auth_views import CustomTokenObtainPairView, CustomTokenObtainView, CustomTokenRefreshView
from core.views.okta_login_viewset import OktaLoginView
from core.views.okta_callback_viewset import OktaCallbackView

# Your views
# from core.views.user_views import UserCreateView
# from core.views.auth_views import CustomTokenObtainView 
# from core.views.okta_login import OktaLoginViewSet

schema_view = get_schema_view(
    openapi.Info(
        title="Okta API",
        default_version="v1",
        description="API documentation for Okta Integration",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)
# urls.py

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('entities.urls')),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    # path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path("api/token/", CustomTokenObtainView.as_view(), name="token_obtain_pair"),
    # path("user/", UserCreateView.as_view({"post": "post"}), name="create-user"),
    path("okta/login/", OktaLoginView.as_view(), name="okta_login"),
    path("okta/callback/", OktaCallbackView.as_view(), name="okta-callback"),
    path("okta/logout/", OktaLogoutView.as_view(), name="okta-logout"),
]
    # path("user/", UserCreateView.as_view({"post": "post"}), name="create-user"),
    # path('okta_user/', OktaLoginViewSet.as_view({"post": "create"}), name='okta-login'),
    # path("api/custom-token/", CustomTokenObtainView.as_view(), name="custom_token_obtain"),
