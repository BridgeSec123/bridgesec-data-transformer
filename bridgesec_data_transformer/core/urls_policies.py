from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core.views.policy_views import PolicyViewSet, UserRoleUpdateView

router = DefaultRouter()
router.register(r"api/policies", PolicyViewSet, basename="policy")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "api/users/<str:pk>/role/",
        UserRoleUpdateView.as_view(),
        name="user-role-update",
    ),
]
