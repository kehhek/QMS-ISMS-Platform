from rest_framework import serializers

from .models import Document, DocumentRevision, Risk, Audit, CorrectiveAction


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
            'audit', 'risk', 'due_date', 'closed_date', 'created_at', 'updated_at',
        )
        read_only_fields = ('created_at', 'updated_at')
