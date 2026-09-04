from django.contrib import admin
from .models import Document, DocumentRevision, Risk, Audit, CorrectiveAction


class DocumentRevisionInline(admin.TabularInline):
    model = DocumentRevision
    extra = 0
    readonly_fields = ('version', 'content', 'status', 'changed_by', 'created_at')
    can_delete = False


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'version', 'owner', 'reviewed_at', 'created_at')
    list_filter = ('status',)
    search_fields = ('title', 'content')
    inlines = [DocumentRevisionInline]

    def save_model(self, request, obj, form, change):
        if change:
            obj._revision_actor = request.user
        super().save_model(request, obj, form, change)


@admin.register(Risk)
class RiskAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'likelihood', 'impact', 'owner', 'target_date', 'created_at')
    list_filter = ('status',)


@admin.register(Audit)
class AuditAdmin(admin.ModelAdmin):
    list_display = ('title', 'audit_type', 'status', 'auditor', 'scheduled_date', 'completed_date')
    list_filter = ('audit_type', 'status')
    search_fields = ('title', 'scope', 'findings')
    filter_horizontal = ('related_documents',)


@admin.register(CorrectiveAction)
class CorrectiveActionAdmin(admin.ModelAdmin):
    list_display = ('title', 'action_type', 'status', 'owner', 'audit', 'risk', 'due_date', 'closed_date')
    list_filter = ('action_type', 'status')
    search_fields = ('title', 'description')
