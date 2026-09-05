from django.urls import path, include
from django.http import JsonResponse
from rest_framework.routers import DefaultRouter

from .views import (
    DocumentViewSet, DocumentRevisionViewSet, RiskViewSet, SupplierViewSet, SupplierQuestionnaireViewSet,
    ControlViewSet, IncidentViewSet, AuditViewSet, CorrectiveActionViewSet, EvidenceViewSet, WorkflowViewSet,
    WorkflowStepViewSet, AuditLogViewSet, ElectronicSignatureViewSet, CoreContentTypesView,
    DashboardSummaryView, TrainingRecordViewSet, IsmsCalendarView, ApprovalMatrixView,
    AssetViewSet, NonconformanceViewSet, ApprovalMatrixRuleViewSet, ApprovalRecordViewSet,
    CalendarEventViewSet, PolicyTemplateListView, PolicyTemplateGenerateView,
    PublicQuestionnaireView, PublicTrustCenterView,
)
from .reports import ControlsStatusReportView


def ping(request):
    return JsonResponse({'ok': True})


router = DefaultRouter()
router.register(r'documents', DocumentViewSet, basename='document')
router.register(r'document-revisions', DocumentRevisionViewSet, basename='document-revision')
router.register(r'assets', AssetViewSet, basename='asset')
router.register(r'risks', RiskViewSet, basename='risk')
router.register(r'suppliers', SupplierViewSet, basename='supplier')
router.register(r'supplier-questionnaires', SupplierQuestionnaireViewSet, basename='supplier-questionnaire')
router.register(r'controls', ControlViewSet, basename='control')
router.register(r'incidents', IncidentViewSet, basename='incident')
router.register(r'audits', AuditViewSet, basename='audit')
router.register(r'corrective-actions', CorrectiveActionViewSet, basename='corrective-action')
router.register(r'nonconformances', NonconformanceViewSet, basename='nonconformance')
router.register(r'evidence', EvidenceViewSet, basename='evidence')
router.register(r'workflows', WorkflowViewSet, basename='workflow')
router.register(r'workflow-steps', WorkflowStepViewSet, basename='workflow-step')
router.register(r'audit-log', AuditLogViewSet, basename='audit-log')
router.register(r'signatures', ElectronicSignatureViewSet, basename='signature')
router.register(r'training-records', TrainingRecordViewSet, basename='training-record')
router.register(r'approval-matrix-rules', ApprovalMatrixRuleViewSet, basename='approval-matrix-rule')
router.register(r'approval-records', ApprovalRecordViewSet, basename='approval-record')
router.register(r'calendar-events', CalendarEventViewSet, basename='calendar-event')

urlpatterns = [
    path('ping/', ping),
    path('content-types/', CoreContentTypesView.as_view(), name='core-content-types'),
    path('dashboard-summary/', DashboardSummaryView.as_view(), name='dashboard-summary'),
    path('isms-calendar/', IsmsCalendarView.as_view(), name='isms-calendar'),
    path('approval-matrix/', ApprovalMatrixView.as_view(), name='approval-matrix'),
    path('policy-templates/', PolicyTemplateListView.as_view(), name='policy-templates'),
    path('policy-templates/<slug:slug>/generate/', PolicyTemplateGenerateView.as_view(), name='policy-template-generate'),
    path('public/questionnaires/<str:token>/', PublicQuestionnaireView.as_view(), name='public-questionnaire'),
    path('public/trust-center/', PublicTrustCenterView.as_view(), name='public-trust-center'),
    path('reports/controls-status/', ControlsStatusReportView.as_view(), name='controls-status-report'),
    path('', include(router.urls)),
]
