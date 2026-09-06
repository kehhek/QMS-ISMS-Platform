from rest_framework import serializers

from .models import (
    Document, DocumentRevision, Risk, Supplier, SupplierQuestionnaire, SupplierAgreement, Control,
    Incident, Audit, CorrectiveAction, Evidence, Workflow, WorkflowStep, AuditLog, ElectronicSignature,
    TrainingRecord, TrainingVideo,
    Asset, AssetReview, Nonconformance, ApprovalMatrixRule, ApprovalRecord, CalendarEvent,
)


class CalendarEventSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, default=None)

    class Meta:
        model = CalendarEvent
        fields = (
            'id', 'title', 'description', 'date', 'created_by', 'created_by_username',
            'created_at', 'updated_at',
        )
        read_only_fields = ('created_by', 'created_at', 'updated_at')


class AssetReviewSerializer(serializers.ModelSerializer):
    reviewed_by_username = serializers.CharField(source='reviewed_by.username', read_only=True, default=None)

    class Meta:
        model = AssetReview
        fields = ('id', 'asset', 'reviewed_by', 'reviewed_by_username', 'reviewed_at', 'outcome', 'notes')
        read_only_fields = ('reviewed_by', 'reviewed_at')


class AssetSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.username', read_only=True, default=None)
    # The last completed review, if any — same "the register alone isn't
    # the evidence, a dated review of it is" pattern as Membership's
    # last_review (tenants/serializers.py).
    last_review = serializers.SerializerMethodField()

    class Meta:
        model = Asset
        fields = (
            'id', 'asset_id', 'name', 'description', 'asset_type', 'sensitivity', 'status',
            'owner', 'owner_username', 'last_review', 'created_at', 'updated_at',
        )
        read_only_fields = ('created_at', 'updated_at')

    def get_last_review(self, obj):
        review = obj.reviews.first()  # AssetReview.Meta.ordering = ['-reviewed_at']
        if not review:
            return None
        return AssetReviewSerializer(review).data


class DocumentRevisionSerializer(serializers.ModelSerializer):
    changed_by_username = serializers.CharField(source='changed_by.username', read_only=True, default=None)

    class Meta:
        model = DocumentRevision
        fields = ('id', 'document', 'version', 'content', 'status', 'changed_by', 'changed_by_username', 'created_at')
        read_only_fields = fields


class DocumentSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.username', read_only=True, default=None)
    reviewer_username = serializers.CharField(source='reviewer.username', read_only=True, default=None)
    approver_username = serializers.CharField(source='approver.username', read_only=True, default=None)

    class Meta:
        model = Document
        fields = (
            'id', 'doc_id', 'category', 'title', 'content', 'file', 'version', 'status', 'classification',
            'owner', 'owner_username', 'reviewer', 'reviewer_username', 'approver', 'approver_username',
            'reviewed_at', 'created_at', 'updated_at',
        )
        # status is read-only here on purpose: it must only ever change via
        # WorkflowStepViewSet.decide() completing an approval (which sets it
        # directly on the model, bypassing this serializer entirely) — never
        # a plain PATCH. Otherwise anyone with document-write access could
        # set status="approved" themselves, skipping the approval workflow
        # and the 21 CFR Part 11 electronic signature it requires entirely.
        # reviewer/approver ARE plain-writable — they're informational
        # assignment, not the enforced approval gate (see Document's
        # docstring comment on those fields).
        read_only_fields = ('version', 'status', 'created_at', 'updated_at')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.file:
            # Same reasoning as EvidenceSerializer: point at our own
            # authenticated download action, not the storage backend's
            # own URL (local disk's /media/ has no auth check at all, and
            # a private S3 object can't be handed out as a plain link).
            data['file'] = f'/api/documents/{instance.pk}/download/'
        return data


class RiskSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source='asset.name', read_only=True, default=None)

    class Meta:
        model = Risk
        fields = (
            'id', 'name', 'description', 'likelihood', 'impact', 'status', 'owner', 'asset', 'asset_name',
            'treatment_plan', 'target_date', 'residual_likelihood', 'residual_impact', 'created_at',
        )
        read_only_fields = ('created_at',)


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = (
            'id', 'name', 'description', 'contact_name', 'contact_email', 'contact_phone',
            'website', 'status', 'risks', 'notes', 'created_at', 'updated_at',
        )
        read_only_fields = ('created_at', 'updated_at')


class SupplierQuestionnaireSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    sent_by_username = serializers.CharField(source='sent_by.username', read_only=True, default=None)
    reviewed_by_username = serializers.CharField(source='reviewed_by.username', read_only=True, default=None)
    decided_by_username = serializers.CharField(source='decided_by.username', read_only=True, default=None)
    question_count = serializers.SerializerMethodField()

    class Meta:
        model = SupplierQuestionnaire
        fields = (
            'id', 'supplier', 'supplier_name', 'title', 'questions', 'question_count', 'status',
            'access_token', 'sent_at', 'sent_by', 'sent_by_username', 'responses', 'responded_at',
            'reviewed_at', 'reviewed_by', 'reviewed_by_username', 'decided_at', 'decided_by',
            'decided_by_username', 'created_at', 'updated_at',
        )
        # status/sent_*/responses/responded_at/reviewed_*/decided_* only
        # ever change via the send/review/approve/reject actions or the
        # supplier's own public response — never a direct PATCH (same
        # reasoning as Document's status field: a plain PATCH here would
        # let an admin fabricate a "responded"/"approved" questionnaire
        # without the supplier ever answering or a real decision made).
        read_only_fields = (
            'status', 'access_token', 'sent_at', 'sent_by', 'responses', 'responded_at',
            'reviewed_at', 'reviewed_by', 'decided_at', 'decided_by', 'created_at', 'updated_at',
        )

    def get_question_count(self, obj):
        return len(obj.questions or [])


class SupplierAgreementSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    sent_by_username = serializers.CharField(source='sent_by.username', read_only=True, default=None)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, default=None)

    class Meta:
        model = SupplierAgreement
        fields = (
            'id', 'supplier', 'supplier_name', 'questionnaire', 'title', 'content', 'file', 'status',
            'access_token', 'sent_at', 'sent_by', 'sent_by_username', 'signed_at', 'signer_name',
            'signer_title', 'created_by', 'created_by_username', 'created_at',
        )
        # status/sent_*/signed_*/signer_* only ever change via the send
        # action or the supplier's own public signature — never a direct
        # PATCH, same reasoning as SupplierQuestionnaire's read-only set.
        read_only_fields = (
            'status', 'access_token', 'sent_at', 'sent_by', 'signed_at', 'signer_name',
            'signer_title', 'created_by', 'created_at',
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.file:
            # Same reasoning as Document/Evidence: point at our own
            # authenticated download action, never a raw storage URL.
            data['file'] = f'/api/supplier-agreements/{instance.pk}/download/'
        return data


class ControlSerializer(serializers.ModelSerializer):
    class Meta:
        model = Control
        fields = (
            'id', 'framework', 'identifier', 'name', 'description', 'status', 'owner',
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
            'id', 'title', 'description', 'action_type', 'status', 'owner', 'root_cause',
            'effectiveness_notes', 'audit', 'risk', 'incident', 'due_date', 'closed_date',
            'created_at', 'updated_at',
        )
        # closed_date/effectiveness_notes are set only by the signed close
        # action (CorrectiveActionViewSet.close), not a plain PATCH — see
        # that view's perform_update, which additionally blocks setting
        # status=closed directly (the same bypass Document.status once had).
        read_only_fields = ('closed_date', 'effectiveness_notes', 'created_at', 'updated_at')


class NonconformanceSerializer(serializers.ModelSerializer):
    reported_by_username = serializers.CharField(source='reported_by.username', read_only=True, default=None)

    class Meta:
        model = Nonconformance
        fields = (
            'id', 'title', 'description', 'status', 'reported_by', 'reported_by_username',
            'closure_reason', 'resulting_capa', 'created_at', 'updated_at',
        )
        # status/closure_reason/resulting_capa only change via the
        # close_no_action/escalate actions (NonconformanceViewSet) — never
        # a plain PATCH, so triage is always a deliberate, logged act.
        read_only_fields = (
            'status', 'reported_by', 'closure_reason', 'resulting_capa', 'created_at', 'updated_at',
        )


class ApprovalMatrixRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalMatrixRule
        fields = ('id', 'entity_type', 'required_role', 'active', 'created_at', 'updated_at')
        read_only_fields = ('created_at', 'updated_at')

    def validate_required_role(self, value):
        if value not in ('admin', 'auditor', 'user'):
            raise serializers.ValidationError('required_role must be one of: admin, auditor, user.')
        return value


class ApprovalRecordSerializer(serializers.ModelSerializer):
    approved_by_username = serializers.CharField(source='approved_by.username', read_only=True)

    class Meta:
        model = ApprovalRecord
        fields = (
            'id', 'entity_type', 'object_id', 'approved_by', 'approved_by_username',
            'document_number', 'review_date', 'approved_at',
        )
        read_only_fields = ('approved_by', 'approved_at')


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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.file:
            # Points at EvidenceViewSet.download, not the storage
            # backend's own URL for the file: local disk's /media/ is
            # served with no auth check at all (DEBUG-only static()), and
            # an S3 object private enough to need real access control
            # can't be handed out as a plain link either. This relative,
            # same-origin API path goes through our own auth/RBAC and
            # works identically for either storage backend.
            data['file'] = f'/api/evidence/{instance.pk}/download/'
        return data


class TrainingVideoSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, default=None)
    my_status = serializers.SerializerMethodField()
    my_record_id = serializers.SerializerMethodField()
    pending_count = serializers.SerializerMethodField()
    in_progress_count = serializers.SerializerMethodField()
    completed_count = serializers.SerializerMethodField()

    class Meta:
        model = TrainingVideo
        fields = (
            'id', 'title', 'description', 'file', 'period', 'created_by', 'created_by_username',
            'created_at', 'my_status', 'my_record_id', 'pending_count', 'in_progress_count', 'completed_count',
        )
        read_only_fields = ('created_by', 'created_at')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.file:
            # Same reasoning as Document/Evidence: point at our own
            # authenticated stream action, never a raw storage URL.
            data['file'] = f'/api/training-videos/{instance.pk}/stream/'
        return data

    def _assignments(self, obj):
        # Cached on the instance per-request: my_status/pending_count/
        # in_progress_count/completed_count would otherwise each run
        # their own query over `assignments` for every video row.
        if not hasattr(obj, '_cached_assignments'):
            obj._cached_assignments = list(obj.assignments.all())
        return obj._cached_assignments

    def _count(self, obj, status_value):
        return sum(1 for a in self._assignments(obj) if a.status == status_value)

    def get_pending_count(self, obj):
        return self._count(obj, 'assigned')

    def get_in_progress_count(self, obj):
        return self._count(obj, 'in_progress')

    def get_completed_count(self, obj):
        return self._count(obj, 'completed')

    def _my_assignment(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        return next((a for a in self._assignments(obj) if a.user_id == request.user.id), None)

    def get_my_status(self, obj):
        assignment = self._my_assignment(obj)
        return assignment.status if assignment else None

    def get_my_record_id(self, obj):
        assignment = self._my_assignment(obj)
        return assignment.id if assignment else None


class TrainingRecordSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    video_title = serializers.CharField(source='video.title', read_only=True, default=None)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = TrainingRecord
        fields = (
            'id', 'user', 'username', 'video', 'video_title', 'title', 'status', 'assigned_date',
            'due_date', 'completed_date', 'notes', 'is_overdue', 'created_at', 'updated_at',
        )
        read_only_fields = ('assigned_date', 'created_at', 'updated_at')


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


class ElectronicSignatureSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    content_type_name = serializers.CharField(source='content_type.model', read_only=True)
    valid = serializers.SerializerMethodField()

    class Meta:
        model = ElectronicSignature
        fields = (
            'id', 'user', 'username', 'printed_name', 'meaning', 'content_type', 'content_type_name',
            'object_id', 'target_repr', 'signed_at', 'valid',
        )
        read_only_fields = fields

    def get_valid(self, obj):
        return obj.verify()
