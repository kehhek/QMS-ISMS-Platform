from django.urls import path, include
from .views import (
    onboard_tenant, RegisterView, LoggingObtainAuthToken, LoginView, LogoutView, UserViewSet, GroupViewSet,
)
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'groups', GroupViewSet, basename='group')

urlpatterns = [
    path('onboard/', onboard_tenant, name='tenant-onboard'),
    path('register/', RegisterView.as_view(), name='api-register'),
    path('token/', LoggingObtainAuthToken.as_view(), name='api-token'),
    path('login/', LoginView.as_view(), name='api-login'),
    path('logout/', LogoutView.as_view(), name='api-logout'),
    path('', include(router.urls)),
]
