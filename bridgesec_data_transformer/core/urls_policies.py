from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core.views.policy_views import PolicyViewSet, UserRoleUpdateView
from core.views.user_management_viewset import UserManagementViewSet
from core.views.role_viewset import RoleListCreateView, RoleDetailView

router = DefaultRouter()
router.register(r"api/policies", PolicyViewSet, basename="policy")
router.register(r"api/users",    UserManagementViewSet, basename="user")

urlpatterns = [
    path("", include(router.urls)),

    # Legacy role-update endpoint (deprecated — use /api/users/<id>/roles/ instead)
    path(
        "api/users/<str:pk>/role/",
        UserRoleUpdateView.as_view(),
        name="user-role-update",
    ),

    # Role management
    path("api/roles/",          RoleListCreateView.as_view(), name="role-list-create"),
    path("api/roles/<str:name>/", RoleDetailView.as_view(),  name="role-detail"),
]
