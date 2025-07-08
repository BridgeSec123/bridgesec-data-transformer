from django.urls import include, path
from rest_framework.routers import DefaultRouter
# from entities.views.user_view import UserEntityViewSet
# from entities.views.group_view import GroupEntity1ViewSet
# from entities.views.user_type_view import UserTypeEntityViewSet
from entities.views.bulk_view import BulkEntityViewSet
# from entities.views.domain_view import DomainEntityViewSet
# from entities.views.org_view import OrgEntityViewSet
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

router = DefaultRouter()
# router.register(r"users", UserEntityViewSet, basename="users")
# router.register(r"groups", GroupEntity1ViewSet, basename="groups")
# router.register(r"user-types", UserTypeEntityViewSet, basename="user-types")
# router.register(r"domains", DomainEntityViewSet, basename="domains")
# router.register(r"orgs", OrgEntityViewSet, basename="orgs")

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
    path("api/bulk/", BulkEntityViewSet.as_view({"post": "post", "get":"fetch_stored_data"}), name="bulk-api"),
    path("fetch_db/", BulkEntityViewSet.as_view({"get": "list_databases"}), name="fetch-db"),
    path("resources/", BulkEntityViewSet.as_view({"get": "get_resource_names"}), name="resources"),
    path("data/<str:date_str>/<str:entity_name>/", BulkEntityViewSet.as_view({"get": "get_resource_data"}), name="data")
]