from django.conf import settings
from django.db import models


class Document(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        IN_REVIEW = 'in_review', 'In review'
        APPROVED = 'approved', 'Approved'
        ARCHIVED = 'archived', 'Archived'

    title = models.CharField(max_length=255)
    content = models.TextField(blank=True)
    version = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='owned_documents',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        """Snapshot the previous content/status into a DocumentRevision and
        bump the version whenever an existing document actually changes.

        Callers can attach `_revision_actor` (a user instance) before saving
        to record who made the change; see core.views.DocumentViewSet.
        """
        if self.pk:
            try:
                old = Document.objects.get(pk=self.pk)
            except Document.DoesNotExist:
                old = None
            if old and (old.content != self.content or old.status != self.status):
                DocumentRevision.objects.create(
                    document=old,
                    version=old.version,
                    content=old.content,
                    status=old.status,
                    changed_by=getattr(self, '_revision_actor', None),
                )
                self.version = old.version + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class DocumentRevision(models.Model):
    """Read-only snapshot of a Document as it existed before an edit."""

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='revisions')
    version = models.IntegerField()
    content = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Document.Status.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version']

    def __str__(self):
        return f'{self.document.title} v{self.version}'


class Risk(models.Model):
    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        MITIGATING = 'mitigating', 'Mitigating'
        CLOSED = 'closed', 'Closed'

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    likelihood = models.IntegerField(default=1)
    impact = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    owner = models.CharField(max_length=255, blank=True)
    treatment_plan = models.TextField(blank=True)
    target_date = models.DateField(null=True, blank=True)
    residual_likelihood = models.IntegerField(null=True, blank=True)
    residual_impact = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Audit(models.Model):
    class AuditType(models.TextChoices):
        INTERNAL = 'internal', 'Internal'
        EXTERNAL = 'external', 'External'
        CERTIFICATION = 'certification', 'Certification'

    class Status(models.TextChoices):
        PLANNED = 'planned', 'Planned'
        IN_PROGRESS = 'in_progress', 'In progress'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    title = models.CharField(max_length=255)
    scope = models.TextField(blank=True)
    audit_type = models.CharField(max_length=20, choices=AuditType.choices, default=AuditType.INTERNAL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED)
    auditor = models.CharField(max_length=255, blank=True, help_text='Name of the lead auditor')
    scheduled_date = models.DateField(null=True, blank=True)
    completed_date = models.DateField(null=True, blank=True)
    findings = models.TextField(blank=True)
    related_documents = models.ManyToManyField(Document, blank=True, related_name='audits')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-scheduled_date', '-created_at']

    def __str__(self):
        return self.title


class CorrectiveAction(models.Model):
    """A CAPA item: a corrective or preventive action, typically raised from
    an audit finding or a risk that needs treatment."""

    class ActionType(models.TextChoices):
        CORRECTIVE = 'corrective', 'Corrective'
        PREVENTIVE = 'preventive', 'Preventive'

    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        IN_PROGRESS = 'in_progress', 'In progress'
        VERIFIED = 'verified', 'Verified'
        CLOSED = 'closed', 'Closed'

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    action_type = models.CharField(max_length=20, choices=ActionType.choices, default=ActionType.CORRECTIVE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    owner = models.CharField(max_length=255, blank=True)
    audit = models.ForeignKey(
        Audit, null=True, blank=True, on_delete=models.SET_NULL, related_name='corrective_actions',
    )
    risk = models.ForeignKey(
        Risk, null=True, blank=True, on_delete=models.SET_NULL, related_name='corrective_actions',
    )
    due_date = models.DateField(null=True, blank=True)
    closed_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Corrective/Preventive Action'

    def __str__(self):
        return self.title
