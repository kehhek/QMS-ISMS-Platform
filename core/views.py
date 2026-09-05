from django.contrib.contenttypes.models import ContentType
from django.db.models import Count
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from tenants.permissions import HasTenantRole, HasTenantRoleStrict, get_role

from .audit import log_action
from .calendar import get_isms_calendar_events
from .export import CsvExportMixin
from .signatures import create_signature
from .models import (
    Document, DocumentRevision, Risk, Supplier, Control, Incident, Audit, CorrectiveAction,
    Evidence, Workflow, WorkflowStep, AuditLog, ElectronicSignature, TrainingRecord,
)
from .serializers import (
    DocumentSerializer, DocumentRevisionSerializer, RiskSerializer, SupplierSerializer, ControlSerializer,
    IncidentSerializer, AuditSerializer, CorrectiveActionSerializer, EvidenceSerializer,
    WorkflowSerializer, WorkflowStepSerializer, AuditLogSerializer, ElectronicSignatureSerializer,
    TrainingRecordSerializer,
)


class AuditLoggingMixin:
    """Writes an AuditLog row for create/update/destroy on this viewset.

    The actor is read from self.request.user, which DRF has already
    resolved via whichever authentication class matched (Token included)
    by the time perform_create/update/destroy run — unlike middleware or
    model signals, which only ever see Django's session-authenticated
    user and would silently miss every token-authenticated API call.
    """

    def _log(self, action_name, instance):
        log_action(self.request.user, action_name, instance)

    def perform_create(self, serializer):
        instance = serializer.save()
        self._log(AuditLog.Action.CREATE, instance)

    def perform_update(self, serializer):
        instance = serializer.save()
        self._log(AuditLog.Action.UPDATE, instance)

    def perform_destroy(self, instance):
        self._log(AuditLog.Action.DELETE, instance)
        instance.delete()


class DocumentViewSet(CsvExportMixin, AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [HasTenantRole]
    # Auditors review documents but shouldn't be the ones editing them.
    allowed_roles = ['admin', 'user']

    def perform_update(self, serializer):
        # Document.save() reads this to attribute the resulting DocumentRevision.
        if serializer.instance is not None:
            serializer.instance._revision_actor = self.request.user
        instance = serializer.save()
        self._log(AuditLog.Action.UPDATE, instance)


class DocumentRevisionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DocumentRevisionSerializer
    permission_classes = [HasTenantRole]

    def get_queryset(self):
        qs = DocumentRevision.objects.all()
        document_id = self.request.query_params.get('document')
        if document_id:
            qs = qs.filter(document_id=document_id)
        return qs


class RiskViewSet(CsvExportMixin, AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = Risk.objects.all()
    serializer_class = RiskSerializer
    permission_classes = [HasTenantRole]
    allowed_roles = ['admin', 'user']


class SupplierViewSet(CsvExportMixin, AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [HasTenantRole]
    allowed_roles = ['admin', 'user']


class ControlViewSet(CsvExportMixin, AuditLoggingMixin, viewsets.ModelViewSet):
    serializer_class = ControlSerializer
    permission_classes = [HasTenantRole]
    allowed_roles = ['admin', 'user']

    def get_queryset(self):
        qs = Control.objects.all()
        framework = self.request.query_params.get('framework')
        if framework:
            qs = qs.filter(framework=framework)
        return qs


class IncidentViewSet(CsvExportMixin, AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = Incident.objects.all()
    serializer_class = IncidentSerializer
    permission_classes = [HasTenantRole]
    # Anyone in the org can report an incident.
    allowed_roles = ['admin', 'auditor', 'user']

    def perform_create(self, serializer):
        instance = serializer.save(reported_by=self.request.user)
        self._log(AuditLog.Action.CREATE, instance)


class AuditViewSet(CsvExportMixin, AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = Audit.objects.all()
    serializer_class = AuditSerializer
    permission_classes = [HasTenantRole]
    allowed_roles = ['admin', 'auditor']


class CorrectiveActionViewSet(CsvExportMixin, AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = CorrectiveAction.objects.all()
    serializer_class = CorrectiveActionSerializer
    permission_classes = [HasTenantRole]
    # Any tenant member can raise/work a CAPA item.
    allowed_roles = ['admin', 'auditor', 'user']


class EvidenceViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = Evidence.objects.all()
    serializer_class = EvidenceSerializer
    permission_classes = [HasTenantRole]
    allowed_roles = ['admin', 'auditor', 'user']

    def perform_create(self, serializer):
        instance = serializer.save(uploaded_by=self.request.user)
        self._log(AuditLog.Action.CREATE, instance)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Streams the decrypted file back through our own authentication
        and per-tenant RBAC (get_object() already enforced both) —
        deliberately NOT a redirect to the storage backend's own URL.
        `/media/...` (local disk, DEBUG only) is served with no auth check
        at all, and an S3 object private enough to need real access
        control can't be handed out as a plain fetchable link either.
        Works identically for local disk and S3 since both storage
        backends' .open() already decrypts (core/storage.py)."""
        from django.http import FileResponse

        evidence = self.get_object()
        return FileResponse(
            evidence.file.open('rb'), as_attachment=True,
            filename=evidence.title or evidence.file.name.rsplit('/', 1)[-1],
        )


class WorkflowViewSet(CsvExportMixin, AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = Workflow.objects.prefetch_related('steps').all()
    serializer_class = WorkflowSerializer
    permission_classes = [HasTenantRole]
    allowed_roles = ['admin', 'user']

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        self._log(AuditLog.Action.CREATE, instance)


class TrainingRecordViewSet(CsvExportMixin, AuditLoggingMixin, viewsets.ModelViewSet):
    """Security awareness training tracking (ISO 27001 A.6.3). Any tenant
    member can read (visibility into who's trained is part of the point
    of a register) and mark their OWN record complete via the `complete`
    action; assigning/editing/deleting records is admin/auditor only.

    No `allowed_roles` class attribute here deliberately — that would
    gate every write (including `complete` on one's own record) at the
    permission-check layer before this view's code ever runs. Instead
    HasTenantRole is left permissive for any-member writes, and the
    admin/auditor restriction on assignment is enforced explicitly in
    perform_create/update/destroy below.
    """

    queryset = TrainingRecord.objects.select_related('user').all()
    serializer_class = TrainingRecordSerializer
    permission_classes = [HasTenantRole]

    def _require_admin_or_auditor(self, request):
        if request.user.is_superuser:
            return
        if get_role(request.user) not in ('admin', 'auditor'):
            raise PermissionDenied('Only admins/auditors can assign or edit training records.')

    def perform_create(self, serializer):
        self._require_admin_or_auditor(self.request)
        instance = serializer.save()
        self._log(AuditLog.Action.CREATE, instance)

    def perform_update(self, serializer):
        self._require_admin_or_auditor(self.request)
        instance = serializer.save()
        self._log(AuditLog.Action.UPDATE, instance)

    def perform_destroy(self, instance):
        self._require_admin_or_auditor(self.request)
        self._log(AuditLog.Action.DELETE, instance)
        instance.delete()

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        record = self.get_object()
        if record.user_id != request.user.pk and not request.user.is_superuser:
            if get_role(request.user) not in ('admin', 'auditor'):
                raise PermissionDenied('You can only complete your own training record.')
        record.status = TrainingRecord.Status.COMPLETED
        record.completed_date = timezone.now().date()
        record.save()
        self._log(AuditLog.Action.UPDATE, record)
        return Response(TrainingRecordSerializer(record).data)


class WorkflowStepViewSet(viewsets.ReadOnlyModelViewSet):
    """Steps are created only via Workflow's nested `new_steps` write; the
    one mutation exposed here is deciding a pending step."""

    queryset = WorkflowStep.objects.select_related('workflow', 'workflow__document').all()
    serializer_class = WorkflowStepSerializer
    permission_classes = [HasTenantRole]

    @action(detail=True, methods=['post'])
    def decide(self, request, pk=None):
        step = self.get_object()
        decision = request.data.get('decision')
        if decision not in ('approved', 'rejected'):
            return Response(
                {'detail': 'decision must be "approved" or "rejected".'}, status=status.HTTP_400_BAD_REQUEST,
            )
        if step.status != WorkflowStep.Status.PENDING:
            return Response({'detail': 'This step has already been decided.'}, status=status.HTTP_400_BAD_REQUEST)

        # Enforce sequential approval: only the lowest-order pending step
        # in this workflow may be decided right now.
        earliest_pending = (
            WorkflowStep.objects.filter(workflow=step.workflow, status=WorkflowStep.Status.PENDING)
            .order_by('order').first()
        )
        if earliest_pending is None or earliest_pending.pk != step.pk:
            return Response({'detail': 'A previous step is still pending.'}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        if step.approver_id:
            allowed = step.approver_id == user.pk
        elif step.approver_role:
            allowed = user.is_superuser or get_role(user) == step.approver_role
        else:
            allowed = user.is_superuser or get_role(user) == 'admin'
        if not allowed:
            raise PermissionDenied('You are not the approver for this step.')

        # 21 CFR Part 11 §11.200(a)(1): an electronic signature must use at
        # least two distinct identification components. Being authenticated
        # (a valid token/session — one component) is deliberately NOT
        # enough on its own to sign; re-entering the password here is the
        # second, at the moment of signing, the same way a handwritten
        # signature is a deliberate act rather than an ambient state.
        password = request.data.get('password')
        if not password or not user.check_password(password):
            log_action(user, AuditLog.Action.SIGNATURE_FAILED, step, metadata={'reason': 'invalid_password'})
            return Response(
                {'detail': 'Incorrect password. Electronic signatures require re-entering your password.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        step.status = WorkflowStep.Status.APPROVED if decision == 'approved' else WorkflowStep.Status.REJECTED
        step.comment = request.data.get('comment', '')
        step.decided_by = user
        step.decided_at = timezone.now()
        step.save()

        log_action(
            user, AuditLog.Action.APPROVE if decision == 'approved' else AuditLog.Action.REJECT, step,
        )
        # The actual Part 11 electronic signature record — separate from
        # the audit log entry above. AuditLog says "an approve action
        # happened"; ElectronicSignature is the signed artifact itself:
        # who, their printed name at the time, what it meant, and a hash
        # linking it to this exact step (see ElectronicSignature.verify()).
        signature_meaning = (
            ElectronicSignature.Meaning.APPROVED if decision == 'approved' else ElectronicSignature.Meaning.REJECTED
        )
        create_signature(user, signature_meaning, step)

        workflow = step.workflow
        if step.status == WorkflowStep.Status.REJECTED:
            workflow.status = Workflow.Status.REJECTED
            workflow.completed_at = timezone.now()
            workflow.save()
        else:
            remaining = WorkflowStep.objects.filter(
                workflow=workflow, status=WorkflowStep.Status.PENDING,
            ).exists()
            if not remaining:
                workflow.status = Workflow.Status.APPROVED
                workflow.completed_at = timezone.now()
                workflow.save()
                document = workflow.document
                document._revision_actor = user
                document.status = Document.Status.APPROVED
                document.save()

        return Response(WorkflowStepSerializer(step).data)


class CoreContentTypesView(APIView):
    """Lets the frontend build an Evidence upload form ("attach to what
    kind of thing") without hardcoding ContentType primary keys, which
    aren't guaranteed stable across environments. ContentType itself is a
    SHARED_APP table (django_content_type lives only in the public
    schema), so these IDs are the same across every tenant — safe to
    fetch once and reuse."""

    permission_classes = [HasTenantRole]

    ATTACHABLE_MODELS = [Document, Risk, Control, Incident, Audit, CorrectiveAction]

    def get(self, request):
        # get_for_model creates the row if it doesn't exist yet, rather
        # than silently omitting a model whose ContentType hasn't been
        # touched before in this environment.
        data = [
            {'id': ContentType.objects.get_for_model(model).id, 'model': model._meta.model_name}
            for model in self.ATTACHABLE_MODELS
        ]
        return Response(data)


class DashboardSummaryView(APIView):
    """Pre-aggregated counts for the dashboard, computed in the DB rather
    than shipping every row (e.g. all 126 Controls) to the browser to
    count client-side. Any tenant member can view — this is read-only,
    org-wide visibility, not a write-gated action."""

    permission_classes = [HasTenantRole]

    @staticmethod
    def _counts_by(queryset, field):
        return {row[field]: row['count'] for row in queryset.values(field).annotate(count=Count('id'))}

    def get(self, request):
        controls_by_framework = {}
        for row in Control.objects.values('framework', 'status').annotate(count=Count('id')):
            controls_by_framework.setdefault(row['framework'], {})[row['status']] = row['count']

        return Response({
            'documents': self._counts_by(Document.objects.all(), 'status'),
            'risks': self._counts_by(Risk.objects.all(), 'status'),
            'audits': self._counts_by(Audit.objects.all(), 'status'),
            'corrective_actions': self._counts_by(CorrectiveAction.objects.all(), 'status'),
            'incidents': self._counts_by(Incident.objects.all(), 'severity'),
            'controls': controls_by_framework,
            'pending_approvals': WorkflowStep.objects.filter(status=WorkflowStep.Status.PENDING).count(),
            'totals': {
                'documents': Document.objects.count(),
                'risks': Risk.objects.count(),
                'audits': Audit.objects.count(),
                'corrective_actions': CorrectiveAction.objects.count(),
                'incidents': Incident.objects.count(),
                'controls': Control.objects.count(),
            },
        })


class AuditLogViewSet(CsvExportMixin, viewsets.ReadOnlyModelViewSet):
    """Read-only by design — AuditLog rows are only ever written by
    AuditLoggingMixin / the workflow decide action, never via a client
    POST. Visibility is restricted to admins/auditors, unlike the other
    viewsets where any tenant member can read."""

    queryset = AuditLog.objects.select_related('actor', 'content_type').all()
    serializer_class = AuditLogSerializer
    permission_classes = [HasTenantRoleStrict]
    allowed_roles = ['admin', 'auditor']


class ElectronicSignatureViewSet(CsvExportMixin, viewsets.ReadOnlyModelViewSet):
    """Read-only — signatures are only ever created by
    WorkflowStepViewSet.decide() after password re-verification, never via
    a direct client POST. Any tenant member can view the signature record
    (this is the evidence a Part 11 audit would ask to see), unlike
    AuditLogViewSet's admin/auditor-only visibility."""

    queryset = ElectronicSignature.objects.select_related('user', 'content_type').all()
    serializer_class = ElectronicSignatureSerializer
    permission_classes = [HasTenantRole]


class IsmsCalendarView(APIView):
    """A single, cross-model calendar of every ISMS date that matters:
    scheduled/planned audits, corrective-action due dates, risk treatment
    target dates, and security-awareness training due dates. Split into
    overdue (past due, not yet closed/completed) and upcoming (due today
    or later), each sorted soonest-first — so "what's late" and "what's
    coming" are each a single glance rather than five separate tabs.

    Read-only, any tenant member — this is a visibility tool, not a
    write-gated action; the underlying records are still edited through
    their own viewsets."""

    permission_classes = [HasTenantRole]

    def get(self, request):
        overdue, upcoming = get_isms_calendar_events()

        def _serialize(e):
            return {**e, 'date': e['date'].isoformat()}

        return Response({
            'overdue': [_serialize(e) for e in overdue],
            'upcoming': [_serialize(e) for e in upcoming],
        })


class ApprovalMatrixView(APIView):
    """Reference table: which tenant roles can write to which record
    types. Read directly off each viewset's own `allowed_roles` (falling
    back to "any member" when a viewset sets none), so this can never
    drift out of sync with what the API actually enforces — it's a
    reflection of the real permission wiring, not a separately
    maintained document that could go stale."""

    permission_classes = [HasTenantRole]

    ALL_ROLES = ['admin', 'auditor', 'user']

    # (label, viewset) — introspected for allowed_roles at request time.
    ENTRIES = [
        ('Documents', DocumentViewSet),
        ('Risks', RiskViewSet),
        ('Suppliers', SupplierViewSet),
        ('Controls', ControlViewSet),
        ('Incidents', IncidentViewSet),
        ('Audits', AuditViewSet),
        ('Corrective/Preventive Actions', CorrectiveActionViewSet),
        ('Evidence', EvidenceViewSet),
        ('Approval Workflows', WorkflowViewSet),
        ('Security Awareness Training (assign/edit)', TrainingRecordViewSet),
    ]

    def get(self, request):
        rows = []
        for label, viewset in self.ENTRIES:
            allowed = getattr(viewset, 'allowed_roles', None) or self.ALL_ROLES
            rows.append({
                'record_type': label,
                'can_write': [r for r in self.ALL_ROLES if r in allowed],
                'can_read': self.ALL_ROLES,
            })
        # A few write rules that aren't a plain viewset allowed_roles
        # lookup — documented here rather than left implicit.
        rows.append({
            'record_type': 'Workflow step approval/rejection (electronic signature)',
            'can_write': ['the specific assigned approver, or the role named on that step'],
            'can_read': self.ALL_ROLES,
        })
        rows.append({
            'record_type': 'Tenant members & roles',
            'can_write': ['admin'],
            'can_read': self.ALL_ROLES,
        })
        rows.append({
            'record_type': 'Org settings / branding',
            'can_write': ['admin'],
            'can_read': self.ALL_ROLES,
        })
        rows.append({
            'record_type': 'Audit log (view only, never written directly)',
            'can_write': [],
            'can_read': ['admin', 'auditor'],
        })
        return Response(rows)
