from django.urls import path, include
from django.http import JsonResponse
from rest_framework.routers import DefaultRouter

from .views import (
    DocumentViewSet, DocumentRevisionViewSet, RiskViewSet, SupplierViewSet, ControlViewSet,
    IncidentViewSet, AuditViewSet, CorrectiveActionViewSet, EvidenceViewSet, WorkflowViewSet,
    WorkflowStepViewSet, AuditLogViewSet, ElectronicSignatureViewSet, CoreContentTypesView,
    DashboardSummaryView, TrainingRecordViewSet, IsmsCalendarView, ApprovalMatrixView,
)
from .reports import ControlsStatusReportView


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
router.register(r'signatures', ElectronicSignatureViewSet, basename='signature')
router.register(r'training-records', TrainingRecordViewSet, basename='training-record')

urlpatterns = [
    path('ping/', ping),
    path('content-types/', CoreContentTypesView.as_view(), name='core-content-types'),
    path('dashboard-summary/', DashboardSummaryView.as_view(), name='dashboard-summary'),
    path('isms-calendar/', IsmsCalendarView.as_view(), name='isms-calendar'),
    path('approval-matrix/', ApprovalMatrixView.as_view(), name='approval-matrix'),
    path('reports/controls-status/', ControlsStatusReportView.as_view(), name='controls-status-report'),
    path('', include(router.urls)),
]
