from django.urls import path, include
from django.http import JsonResponse
from rest_framework.routers import DefaultRouter

from .views import (
    DocumentViewSet, DocumentRevisionViewSet, RiskViewSet, AuditViewSet, CorrectiveActionViewSet,
)


def ping(request):
    return JsonResponse({'ok': True})


router = DefaultRouter()
router.register(r'documents', DocumentViewSet, basename='document')
router.register(r'document-revisions', DocumentRevisionViewSet, basename='document-revision')
router.register(r'risks', RiskViewSet, basename='risk')
router.register(r'audits', AuditViewSet, basename='audit')
router.register(r'corrective-actions', CorrectiveActionViewSet, basename='corrective-action')

urlpatterns = [
    path('ping/', ping),
    path('', include(router.urls)),
]
