from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import TenantSettingsView, MembershipViewSet

router = DefaultRouter()
router.register(r'members', MembershipViewSet, basename='tenant-member')

urlpatterns = [
    path('settings/', TenantSettingsView.as_view(), name='tenant-settings'),
    path('', include(router.urls)),
]
