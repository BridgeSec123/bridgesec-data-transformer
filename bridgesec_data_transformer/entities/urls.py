from django.urls import include, path
from rest_framework.routers import DefaultRouter
from entities.views.bulk_view import BulkEntityViewSet
from entities.views.import_view import ImportResourcesView
from entities.views.confirm_delete_view import ConfirmDeletionView
from entities.views.progress_view import BulkProgressView, BulkProgressStreamView, DiffReportView
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
    path("data/", BulkEntityViewSet.as_view({"get": "get_resource_data"}), name="data"),
    path("restore/<str:db_name>/<str:entity_name>/", BulkEntityViewSet.as_view({"post": "restore_modified_data"}), name="restore-data"),
    path("db-map/", BulkEntityViewSet.as_view({"get": "get_db_map_view"}), name="db-map"),
    path("import/", ImportResourcesView.as_view(), name="import-resources"),
    path("diff-collections/<str:entity_name>/", BulkEntityViewSet.as_view({"get": "diff_collections"}), name="diff-collections"),
    path("entity-schema/<str:entity_name>/", BulkEntityViewSet.as_view({"get": "get_entity_schema"}), name="entity-schema"),
    # path("test-entity/<str:entity_name>/", BulkEntityViewSet.as_view({"get": "test_entity"}), name="test-entity"),
    path("confirm-delete/", ConfirmDeletionView.as_view(), name="confirm-delete"),
    path("api/bulk/progress/", BulkProgressView.as_view(), name="bulk-progress"),
    path("api/bulk/progress/stream/", BulkProgressStreamView.as_view(), name="bulk-progress-stream"),
    path("api/diff-report/<str:db_name>/", DiffReportView.as_view(), name="diff-report"),
]
