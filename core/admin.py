from django.contrib import admin
from .models import (
    Document, DocumentRevision, Risk, Supplier, SupplierQuestionnaire, Control, Incident, Audit,
    CorrectiveAction, Evidence, Workflow, WorkflowStep, AuditLog, ElectronicSignature, TrainingRecord,
    Asset, Nonconformance, ApprovalMatrixRule, ApprovalRecord, CalendarEvent,
)


class DocumentRevisionInline(admin.TabularInline):
    model = DocumentRevision
    extra = 0
    readonly_fields = ('version', 'content', 'status', 'file', 'changed_by', 'created_at')
    can_delete = False


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        'doc_id', 'title', 'category', 'status', 'classification', 'version',
        'owner', 'reviewer', 'approver', 'created_at',
    )
    list_filter = ('category', 'status', 'classification')
    search_fields = ('doc_id', 'title', 'content')
    inlines = [DocumentRevisionInline]

    def save_model(self, request, obj, form, change):
        if change:
            obj._revision_actor = request.user
        super().save_model(request, obj, form, change)


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'created_by', 'created_at')
    search_fields = ('title', 'description')


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('asset_id', 'name', 'asset_type', 'sensitivity', 'status', 'owner', 'created_at')
    list_filter = ('asset_type', 'sensitivity', 'status')
    search_fields = ('asset_id', 'name', 'description')


@admin.register(Risk)
class RiskAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'likelihood', 'impact', 'owner', 'asset', 'target_date', 'created_at')
    list_filter = ('status',)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'contact_name', 'contact_email', 'created_at')
    list_filter = ('status',)
    search_fields = ('name', 'description', 'contact_name', 'contact_email')
    filter_horizontal = ('risks',)


@admin.register(SupplierQuestionnaire)
class SupplierQuestionnaireAdmin(admin.ModelAdmin):
    list_display = ('title', 'supplier', 'status', 'sent_at', 'responded_at', 'created_at')
    list_filter = ('status',)
    search_fields = ('title', 'supplier__name')
    readonly_fields = ('access_token',)


@admin.register(Control)
class ControlAdmin(admin.ModelAdmin):
    list_display = ('framework', 'identifier', 'name', 'status', 'owner')
    list_filter = ('framework', 'status')
    search_fields = ('identifier', 'name', 'description')
    filter_horizontal = ('risks',)


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ('title', 'severity', 'status', 'related_risk', 'detected_at', 'resolved_at')
    list_filter = ('severity', 'status')
    search_fields = ('title', 'description')


@admin.register(Audit)
class AuditAdmin(admin.ModelAdmin):
    list_display = ('title', 'audit_type', 'status', 'auditor', 'scheduled_date', 'completed_date')
    list_filter = ('audit_type', 'status')
    search_fields = ('title', 'scope', 'findings')
    filter_horizontal = ('related_documents',)


@admin.register(CorrectiveAction)
class CorrectiveActionAdmin(admin.ModelAdmin):
    list_display = ('title', 'action_type', 'status', 'owner', 'audit', 'risk', 'incident', 'due_date', 'closed_date')
    list_filter = ('action_type', 'status')
    search_fields = ('title', 'description', 'root_cause')


@admin.register(Nonconformance)
class NonconformanceAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'reported_by', 'resulting_capa', 'created_at')
    list_filter = ('status',)
    search_fields = ('title', 'description')


@admin.register(ApprovalMatrixRule)
class ApprovalMatrixRuleAdmin(admin.ModelAdmin):
    list_display = ('entity_type', 'required_role', 'active', 'updated_at')
    list_filter = ('entity_type', 'active')


@admin.register(ApprovalRecord)
class ApprovalRecordAdmin(admin.ModelAdmin):
    list_display = ('entity_type', 'object_id', 'approved_by', 'approved_at', 'document_number')
    list_filter = ('entity_type',)

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TrainingRecord)
class TrainingRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'status', 'assigned_date', 'due_date', 'completed_date', 'is_overdue')
    list_filter = ('status',)
    search_fields = ('title', 'user__username')

    def is_overdue(self, obj):
        return obj.is_overdue
    is_overdue.boolean = True


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ('title', 'content_type', 'object_id', 'uploaded_by', 'uploaded_at')
    list_filter = ('content_type',)
    search_fields = ('title', 'description')


class WorkflowStepInline(admin.TabularInline):
    model = WorkflowStep
    extra = 0
    readonly_fields = ('status', 'decided_by', 'decided_at')


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ('document', 'status', 'created_by', 'created_at', 'completed_at')
    list_filter = ('status',)
    inlines = [WorkflowStepInline]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'actor', 'action', 'content_type', 'target_repr')
    list_filter = ('action', 'content_type')
    search_fields = ('target_repr',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ElectronicSignature)
class ElectronicSignatureAdmin(admin.ModelAdmin):
    list_display = ('signed_at', 'printed_name', 'meaning', 'content_type', 'target_repr', 'is_valid')
    list_filter = ('meaning', 'content_type')
    search_fields = ('printed_name', 'target_repr')

    def is_valid(self, obj):
        return obj.verify()
    is_valid.boolean = True

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
