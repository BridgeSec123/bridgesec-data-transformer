from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core.views.policy_views import PolicyViewSet
from core.views.user_management_viewset import UserManagementViewSet
from core.views.role_viewset import (
    RoleListCreateView, RoleDetailView,
    RolePermissionsView, RolePermissionsAddView, RolePermissionRemoveView,
    PermissionCatalogView,
)

router = DefaultRouter()
router.register(r"api/policies", PolicyViewSet, basename="policy")
router.register(r"api/users",    UserManagementViewSet, basename="user")

urlpatterns = [
    path("", include(router.urls)),

    # Role management
    path("api/roles/",          RoleListCreateView.as_view(), name="role-list-create"),
    path("api/roles/<str:name>/", RoleDetailView.as_view(),  name="role-detail"),

    # Role <-> permission management
    path("api/roles/<str:name>/permissions/",     RolePermissionsView.as_view(),      name="role-permissions"),
    path("api/roles/<str:name>/permissions/add/", RolePermissionsAddView.as_view(),   name="role-permissions-add"),
    path("api/roles/<str:name>/permissions/<str:perm_name>/", RolePermissionRemoveView.as_view(), name="role-permission-remove"),
    path("api/permissions/",    PermissionCatalogView.as_view(), name="permission-catalog"),
]
