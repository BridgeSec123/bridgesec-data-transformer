from django.urls import include, path
from rest_framework.routers import DefaultRouter
from entities.views.bulk_view import BulkEntityViewSet
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

router = DefaultRouter()

schema_view = get_schema_view(
    openapi.Info(
        title="Your API",
        default_version="v1",
        description="API documentation",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path("", include(router.urls)),
    path("api/bulk/", BulkEntityViewSet.as_view({"post": "post"}), name="bulk-api"),
    # path("fetch_db/", BulkEntityViewSet.as_view({"get": "list_databases"}), name="fetch-db"),
    path("resources/", BulkEntityViewSet.as_view({"get": "get_resource_names"}), name="resources"),
    path("data/<str:date_str>/<str:entity_name>/", BulkEntityViewSet.as_view({"get": "get_resource_data"}), name="data"),
    path("restore/<str:date_str>/<str:entity_name>/", BulkEntityViewSet.as_view({"post": "restore_modified_data"}), name="restore-data")  
]
