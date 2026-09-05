from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import TenantSettingsView, MembershipViewSet, AccessReviewViewSet, UserGroupViewSet

router = DefaultRouter()
router.register(r'members', MembershipViewSet, basename='tenant-member')
router.register(r'access-reviews', AccessReviewViewSet, basename='access-review')
router.register(r'user-groups', UserGroupViewSet, basename='user-group')

urlpatterns = [
    path('settings/', TenantSettingsView.as_view(), name='tenant-settings'),
    path('', include(router.urls)),
]
