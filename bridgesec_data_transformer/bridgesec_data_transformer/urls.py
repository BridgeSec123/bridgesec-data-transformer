from django.contrib import admin
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

from core.views.okta_logout_viewset import OktaLogoutView
from core.views.user_views import UserCreateView
from core.views.auth_views import CustomTokenObtainPairView, CustomTokenObtainView, CustomTokenRefreshView, ResolveTenantView, CurrentTenantView, MyTenantsView
from core.views.okta_login_viewset import OktaLoginView
from core.views.okta_callback_viewset import OktaCallbackView
from core.views.token_retrieval_view import TokenRetrievalView
from core.views.tenant_viewset import (
    TenantListCreateView, TenantDetailView,
    TenantUserListView, TenantUserDetailView,
)
from core.views.tenant_logo_viewset import TenantLogoView
from core.views.chat_viewset import ChatView
from core.views.log_views import LogListView, LogSummaryView, LogTraceView, LogStreamView
from core.views.entity_config_viewset import EntityConfigListView, EntityConfigDetailView, EntityConfigCollectionView
from core.views.scheduler_config_viewset import SchedulerConfigView
from core.views.cross_tenant_summary_view import CrossTenantSummaryView
from core.views.cross_tenant_migrate_view import CrossTenantMigrateView

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
    authentication_classes=[],
)
# urls.py

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls_policies')),
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
    path("api/auth/resolve-tenant/", ResolveTenantView.as_view(), name="resolve-tenant"),
    path("api/auth/me/", CurrentTenantView.as_view(), name="auth-me"),
    path("api/auth/token/", TokenRetrievalView.as_view(), name="auth-token"),
    path("api/auth/my-tenants/", MyTenantsView.as_view(), name="my-tenants"),
    path("api/chat/", ChatView.as_view(), name="chat"),
    # Multi-tenancy management (super-admin only)
    path("api/tenants/", TenantListCreateView.as_view(), name="tenant-list-create"),
    path("api/tenants/<str:tenant_id>/", TenantDetailView.as_view(), name="tenant-detail"),
    path("api/tenants/<str:tenant_id>/users/", TenantUserListView.as_view(), name="tenant-users"),
    path("api/tenants/<str:tenant_id>/users/<str:uid>/", TenantUserDetailView.as_view(), name="tenant-user-detail"),
    path("api/tenants/<str:tenant_id>/logo/", TenantLogoView.as_view(), name="tenant-logo"),
    path("api/logs/",                 LogListView.as_view(),    name="log-list"),
    path("api/logs/summary/",         LogSummaryView.as_view(), name="log-summary"),
    path("api/logs/stream/",          LogStreamView.as_view(),  name="log-stream"),
    path("api/logs/<str:request_id>/", LogTraceView.as_view(), name="log-trace"),
    # Entity backup configuration (per-tenant enable/disable)
    path("api/entity-config/", EntityConfigListView.as_view(), name="entity-config-list"),
    path("api/entity-config/<str:config_name>/", EntityConfigDetailView.as_view(), name="entity-config-detail"),
    path("api/entity-config/<str:entity_name>/collections/<str:collection_name>/", EntityConfigCollectionView.as_view(), name="entity-config-collection"),
    # Scheduler configuration (schedule time + scopes display)
    path("api/scheduler-config/", SchedulerConfigView.as_view(), name="scheduler-config"),
    # Cross-tenant summary (super-admin only)
    path("api/cross-tenant/summary/", CrossTenantSummaryView.as_view(), name="cross-tenant-summary"),
    # Cross-tenant entity migration (super-admin only)
    path("api/cross-tenant-migrate/", CrossTenantMigrateView.as_view(), name="cross-tenant-migrate"),
]
    # path("user/", UserCreateView.as_view({"post": "post"}), name="create-user"),
    # path('okta_user/', OktaLoginViewSet.as_view({"post": "create"}), name='okta-login'),
    # path("api/custom-token/", CustomTokenObtainView.as_view(), name="custom_token_obtain"),
