from django.urls import include, path
from rest_framework.routers import DefaultRouter

# from core.views.group_views import GroupViewSet
# from core.views.user_views import UserViewSet

router = DefaultRouter()
# router.register(r"users", UserViewSet, basename="users")
# router.register(r"groups", GroupViewSet, basename="groups")

urlpatterns = [
    path("", include(router.urls)), 
]