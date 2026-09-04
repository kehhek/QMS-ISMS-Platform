from rest_framework import serializers

from .models import (
    Document, DocumentRevision, Risk, Control, Incident, Audit, CorrectiveAction,
    Evidence, Workflow, WorkflowStep, AuditLog,
)


class DocumentRevisionSerializer(serializers.ModelSerializer):
    changed_by_username = serializers.CharField(source='changed_by.username', read_only=True, default=None)

    class Meta:
        model = DocumentRevision
        fields = ('id', 'document', 'version', 'content', 'status', 'changed_by', 'changed_by_username', 'created_at')
        read_only_fields = fields


class DocumentSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.username', read_only=True, default=None)

    class Meta:
        model = Document
        fields = (
            'id', 'title', 'content', 'version', 'status',
            'owner', 'owner_username', 'reviewed_at', 'created_at', 'updated_at',
        )
        read_only_fields = ('version', 'created_at', 'updated_at')


class RiskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Risk
        fields = (
            'id', 'name', 'description', 'likelihood', 'impact', 'status', 'owner',
            'treatment_plan', 'target_date', 'residual_likelihood', 'residual_impact', 'created_at',
        )
        read_only_fields = ('created_at',)


class ControlSerializer(serializers.ModelSerializer):
    class Meta:
        model = Control
        fields = (
            'id', 'identifier', 'name', 'description', 'status', 'owner',
            'risks', 'created_at', 'updated_at',
        )
        read_only_fields = ('created_at', 'updated_at')


class IncidentSerializer(serializers.ModelSerializer):
    reported_by_username = serializers.CharField(source='reported_by.username', read_only=True, default=None)

    class Meta:
        model = Incident
        fields = (
            'id', 'title', 'description', 'severity', 'status', 'related_risk',
            'reported_by', 'reported_by_username', 'detected_at', 'resolved_at',
            'created_at', 'updated_at',
        )
        read_only_fields = ('reported_by', 'created_at', 'updated_at')


class AuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Audit
        fields = (
            'id', 'title', 'scope', 'audit_type', 'status', 'auditor',
            'scheduled_date', 'completed_date', 'findings', 'related_documents',
            'created_at', 'updated_at',
        )
        read_only_fields = ('created_at', 'updated_at')


class CorrectiveActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CorrectiveAction
        fields = (
            'id', 'title', 'description', 'action_type', 'status', 'owner',
            'audit', 'risk', 'incident', 'due_date', 'closed_date', 'created_at', 'updated_at',
        )
        read_only_fields = ('created_at', 'updated_at')


class EvidenceSerializer(serializers.ModelSerializer):
    uploaded_by_username = serializers.CharField(source='uploaded_by.username', read_only=True, default=None)
    content_type_name = serializers.CharField(source='content_type.model', read_only=True)

    class Meta:
        model = Evidence
        fields = (
            'id', 'title', 'file', 'description', 'uploaded_by', 'uploaded_by_username',
            'content_type', 'content_type_name', 'object_id', 'uploaded_at',
        )
        read_only_fields = ('uploaded_by', 'uploaded_at')


class WorkflowStepSerializer(serializers.ModelSerializer):
    approver_username = serializers.CharField(source='approver.username', read_only=True, default=None)
    decided_by_username = serializers.CharField(source='decided_by.username', read_only=True, default=None)

    class Meta:
        model = WorkflowStep
        fields = (
            'id', 'workflow', 'order', 'approver', 'approver_username', 'approver_role',
            'status', 'comment', 'decided_by', 'decided_by_username', 'decided_at',
        )
        read_only_fields = ('status', 'decided_by', 'decided_at')


class WorkflowStepCreateSerializer(serializers.ModelSerializer):
    """Used only for the nested `steps` write on WorkflowSerializer — no
    workflow/status/decided_* fields, since those are set by the parent."""

    class Meta:
        model = WorkflowStep
        fields = ('order', 'approver', 'approver_role')


class WorkflowSerializer(serializers.ModelSerializer):
    steps = WorkflowStepSerializer(many=True, read_only=True)
    new_steps = WorkflowStepCreateSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = Workflow
        fields = ('id', 'document', 'status', 'created_by', 'created_at', 'completed_at', 'steps', 'new_steps')
        read_only_fields = ('status', 'created_by', 'created_at', 'completed_at')

    def create(self, validated_data):
        steps_data = validated_data.pop('new_steps', [])
        workflow = Workflow.objects.create(**validated_data)
        for step_data in steps_data:
            WorkflowStep.objects.create(workflow=workflow, **step_data)
        return workflow


class AuditLogSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source='actor.username', read_only=True, default=None)
    content_type_name = serializers.CharField(source='content_type.model', read_only=True)

    class Meta:
        model = AuditLog
        fields = (
            'id', 'actor', 'actor_username', 'action', 'content_type', 'content_type_name',
            'object_id', 'target_repr', 'metadata', 'created_at',
        )
        read_only_fields = fields
