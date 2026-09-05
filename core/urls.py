from django.urls import path, include
from django.http import JsonResponse
from rest_framework.routers import DefaultRouter

from .views import (
    DocumentViewSet, DocumentRevisionViewSet, RiskViewSet, SupplierViewSet, ControlViewSet,
    IncidentViewSet, AuditViewSet, CorrectiveActionViewSet, EvidenceViewSet, WorkflowViewSet,
    WorkflowStepViewSet, AuditLogViewSet, CoreContentTypesView, DashboardSummaryView,
)


def ping(request):
    return JsonResponse({'ok': True})


router = DefaultRouter()
router.register(r'documents', DocumentViewSet, basename='document')
router.register(r'document-revisions', DocumentRevisionViewSet, basename='document-revision')
router.register(r'risks', RiskViewSet, basename='risk')
router.register(r'suppliers', SupplierViewSet, basename='supplier')
router.register(r'controls', ControlViewSet, basename='control')
router.register(r'incidents', IncidentViewSet, basename='incident')
router.register(r'audits', AuditViewSet, basename='audit')
router.register(r'corrective-actions', CorrectiveActionViewSet, basename='corrective-action')
router.register(r'evidence', EvidenceViewSet, basename='evidence')
router.register(r'workflows', WorkflowViewSet, basename='workflow')
router.register(r'workflow-steps', WorkflowStepViewSet, basename='workflow-step')
router.register(r'audit-log', AuditLogViewSet, basename='audit-log')

urlpatterns = [
    path('ping/', ping),
    path('content-types/', CoreContentTypesView.as_view(), name='core-content-types'),
    path('dashboard-summary/', DashboardSummaryView.as_view(), name='dashboard-summary'),
    path('', include(router.urls)),
]
