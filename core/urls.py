from django.urls import path, include
from django.http import JsonResponse
from rest_framework.routers import DefaultRouter

from .views import (
    DocumentViewSet, DocumentRevisionViewSet, RiskViewSet, SupplierViewSet, SupplierQuestionnaireViewSet,
    SupplierAgreementViewSet, ControlViewSet, IncidentViewSet, AuditViewSet, CorrectiveActionViewSet,
    EvidenceViewSet, WorkflowViewSet, WorkflowStepViewSet, AuditLogViewSet, ElectronicSignatureViewSet,
    CoreContentTypesView, DashboardSummaryView, TrainingRecordViewSet, TrainingVideoViewSet, QuizQuestionViewSet,
    IsmsCalendarView, ApprovalMatrixView, AssetViewSet, AssetReviewViewSet, NonconformanceViewSet,
    ApprovalMatrixRuleViewSet, ApprovalRecordViewSet, CalendarEventViewSet, PolicyTemplateListView,
    PolicyTemplateGenerateView, PublicQuestionnaireView, PublicAgreementView, PublicAgreementFileView,
    PublicTrustCenterView, AuditorAccessViewSet, PublicAuditorAccessView, PublicAuditorEvidenceFileView,
    PublicAuditorPolicyFileView, IntegrationViewSet, IntegrationCheckResultViewSet,
)
from .reports import ControlsStatusReportView, StatementOfApplicabilityReportView


def ping(request):
    return JsonResponse({'ok': True})


router = DefaultRouter()
router.register(r'documents', DocumentViewSet, basename='document')
router.register(r'document-revisions', DocumentRevisionViewSet, basename='document-revision')
router.register(r'assets', AssetViewSet, basename='asset')
router.register(r'asset-reviews', AssetReviewViewSet, basename='asset-review')
router.register(r'risks', RiskViewSet, basename='risk')
router.register(r'suppliers', SupplierViewSet, basename='supplier')
router.register(r'supplier-questionnaires', SupplierQuestionnaireViewSet, basename='supplier-questionnaire')
router.register(r'supplier-agreements', SupplierAgreementViewSet, basename='supplier-agreement')
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
router.register(r'training-videos', TrainingVideoViewSet, basename='training-video')
router.register(r'quiz-questions', QuizQuestionViewSet, basename='quiz-question')
router.register(r'approval-matrix-rules', ApprovalMatrixRuleViewSet, basename='approval-matrix-rule')
router.register(r'approval-records', ApprovalRecordViewSet, basename='approval-record')
router.register(r'calendar-events', CalendarEventViewSet, basename='calendar-event')
router.register(r'auditor-access', AuditorAccessViewSet, basename='auditor-access')
router.register(r'integrations', IntegrationViewSet, basename='integration')
router.register(r'integration-check-results', IntegrationCheckResultViewSet, basename='integration-check-result')

urlpatterns = [
    path('ping/', ping),
    path('content-types/', CoreContentTypesView.as_view(), name='core-content-types'),
    path('dashboard-summary/', DashboardSummaryView.as_view(), name='dashboard-summary'),
    path('isms-calendar/', IsmsCalendarView.as_view(), name='isms-calendar'),
    path('approval-matrix/', ApprovalMatrixView.as_view(), name='approval-matrix'),
    path('policy-templates/', PolicyTemplateListView.as_view(), name='policy-templates'),
    path('policy-templates/<slug:slug>/generate/', PolicyTemplateGenerateView.as_view(), name='policy-template-generate'),
    path('public/questionnaires/<str:token>/', PublicQuestionnaireView.as_view(), name='public-questionnaire'),
    path('public/agreements/<str:token>/', PublicAgreementView.as_view(), name='public-agreement'),
    path('public/agreements/<str:token>/file/', PublicAgreementFileView.as_view(), name='public-agreement-file'),
    path('public/trust-center/', PublicTrustCenterView.as_view(), name='public-trust-center'),
    path('public/auditor-access/<str:token>/', PublicAuditorAccessView.as_view(), name='public-auditor-access'),
    path(
        'public/auditor-access/<str:token>/evidence/<int:evidence_id>/',
        PublicAuditorEvidenceFileView.as_view(), name='public-auditor-evidence',
    ),
    path(
        'public/auditor-access/<str:token>/policies/<int:document_id>/',
        PublicAuditorPolicyFileView.as_view(), name='public-auditor-policy',
    ),
    path('reports/controls-status/', ControlsStatusReportView.as_view(), name='controls-status-report'),
    path(
        'reports/statement-of-applicability/', StatementOfApplicabilityReportView.as_view(),
        name='statement-of-applicability-report',
    ),
    path('', include(router.urls)),
]
