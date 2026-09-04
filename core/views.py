from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from tenants.permissions import HasTenantRole, HasTenantRoleStrict, get_role

from .models import (
    Document, DocumentRevision, Risk, Control, Incident, Audit, CorrectiveAction,
    Evidence, Workflow, WorkflowStep, AuditLog,
)
from .serializers import (
    DocumentSerializer, DocumentRevisionSerializer, RiskSerializer, ControlSerializer,
    IncidentSerializer, AuditSerializer, CorrectiveActionSerializer, EvidenceSerializer,
    WorkflowSerializer, WorkflowStepSerializer, AuditLogSerializer,
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
        AuditLog.objects.create(
            actor=self.request.user if self.request.user.is_authenticated else None,
            action=action_name,
            content_type=ContentType.objects.get_for_model(instance),
            object_id=instance.pk,
            target_repr=str(instance),
        )

    def perform_create(self, serializer):
        instance = serializer.save()
        self._log(AuditLog.Action.CREATE, instance)

    def perform_update(self, serializer):
        instance = serializer.save()
        self._log(AuditLog.Action.UPDATE, instance)

    def perform_destroy(self, instance):
        self._log(AuditLog.Action.DELETE, instance)
        instance.delete()


class DocumentViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
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


class RiskViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = Risk.objects.all()
    serializer_class = RiskSerializer
    permission_classes = [HasTenantRole]
    allowed_roles = ['admin', 'user']


class ControlViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = Control.objects.all()
    serializer_class = ControlSerializer
    permission_classes = [HasTenantRole]
    allowed_roles = ['admin', 'user']


class IncidentViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = Incident.objects.all()
    serializer_class = IncidentSerializer
    permission_classes = [HasTenantRole]
    # Anyone in the org can report an incident.
    allowed_roles = ['admin', 'auditor', 'user']

    def perform_create(self, serializer):
        instance = serializer.save(reported_by=self.request.user)
        self._log(AuditLog.Action.CREATE, instance)


class AuditViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = Audit.objects.all()
    serializer_class = AuditSerializer
    permission_classes = [HasTenantRole]
    allowed_roles = ['admin', 'auditor']


class CorrectiveActionViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
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


class WorkflowViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = Workflow.objects.prefetch_related('steps').all()
    serializer_class = WorkflowSerializer
    permission_classes = [HasTenantRole]
    allowed_roles = ['admin', 'user']

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        self._log(AuditLog.Action.CREATE, instance)


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

        step.status = WorkflowStep.Status.APPROVED if decision == 'approved' else WorkflowStep.Status.REJECTED
        step.comment = request.data.get('comment', '')
        step.decided_by = user
        step.decided_at = timezone.now()
        step.save()

        AuditLog.objects.create(
            actor=user,
            action=AuditLog.Action.APPROVE if decision == 'approved' else AuditLog.Action.REJECT,
            content_type=ContentType.objects.get_for_model(step),
            object_id=step.pk,
            target_repr=str(step),
        )

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


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only by design — AuditLog rows are only ever written by
    AuditLoggingMixin / the workflow decide action, never via a client
    POST. Visibility is restricted to admins/auditors, unlike the other
    viewsets where any tenant member can read."""

    queryset = AuditLog.objects.select_related('actor', 'content_type').all()
    serializer_class = AuditLogSerializer
    permission_classes = [HasTenantRoleStrict]
    allowed_roles = ['admin', 'auditor']
