from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from .storage import EncryptedFileSystemStorage


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


class Supplier(models.Model):
    """A third-party vendor/supplier, tracked for ISO 27001 A.5.19-A.5.22
    (information security in supplier relationships) and general vendor
    risk management."""

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        UNDER_REVIEW = 'under_review', 'Under review'
        INACTIVE = 'inactive', 'Inactive'

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    contact_name = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    website = models.URLField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UNDER_REVIEW)
    risks = models.ManyToManyField(Risk, blank=True, related_name='suppliers')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Control(models.Model):
    """An ISMS control (e.g. an ISO 27001 Annex A control, or a SOC 2
    Common Criterion) and how well it's implemented, mapped to the risks
    it mitigates. See core/data/control_catalogs.py for the standard
    catalogs and core/management/commands/seed_control_catalogs.py to
    load them into a tenant."""

    class Framework(models.TextChoices):
        ISO27001 = 'iso27001', 'ISO/IEC 27001:2022 Annex A'
        SOC2 = 'soc2', 'SOC 2 (Common Criteria)'
        CUSTOM = 'custom', 'Custom'

    class Status(models.TextChoices):
        NOT_IMPLEMENTED = 'not_implemented', 'Not implemented'
        PARTIAL = 'partial', 'Partially implemented'
        IMPLEMENTED = 'implemented', 'Implemented'
        NOT_APPLICABLE = 'not_applicable', 'Not applicable'

    framework = models.CharField(max_length=20, choices=Framework.choices, default=Framework.ISO27001)
    identifier = models.CharField(max_length=50, help_text='e.g. A.5.1 (ISO 27001) or CC6.1 (SOC 2)')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_IMPLEMENTED)
    owner = models.CharField(max_length=255, blank=True)
    risks = models.ManyToManyField(Risk, blank=True, related_name='controls')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['framework', 'identifier']
        unique_together = ('framework', 'identifier')

    def __str__(self):
        return f'{self.identifier} — {self.name}'


class Incident(models.Model):
    class Severity(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        CRITICAL = 'critical', 'Critical'

    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        INVESTIGATING = 'investigating', 'Investigating'
        CONTAINED = 'contained', 'Contained'
        RESOLVED = 'resolved', 'Resolved'
        CLOSED = 'closed', 'Closed'

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    related_risk = models.ForeignKey(
        Risk, null=True, blank=True, on_delete=models.SET_NULL, related_name='incidents',
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    detected_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


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
    incident = models.ForeignKey(
        Incident, null=True, blank=True, on_delete=models.SET_NULL, related_name='corrective_actions',
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


class Evidence(models.Model):
    """A file attached as evidence to any other core object (an Audit,
    Control, Incident, CorrectiveAction, Risk, or Document) — the
    generic FK lets one upload flow serve all of them."""

    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='evidence/%Y/%m/', storage=EncryptedFileSystemStorage())
    description = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.title


class Workflow(models.Model):
    """An approval workflow run against a Document — an ordered sequence
    of WorkflowSteps that must each approve before the document is
    considered Approved."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        CANCELLED = 'cancelled', 'Cancelled'

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='workflows')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Workflow for {self.document.title} ({self.status})'


class WorkflowStep(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        SKIPPED = 'skipped', 'Skipped'

    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='steps')
    order = models.PositiveIntegerField(default=1)
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
        help_text='A specific approver. Leave blank to require approver_role instead.',
    )
    approver_role = models.CharField(
        max_length=20, blank=True,
        help_text='Tenant role (admin/auditor/user) allowed to decide this step if no specific approver is set.',
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    comment = models.TextField(blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['workflow', 'order']
        unique_together = ('workflow', 'order')

    def __str__(self):
        return f'Step {self.order} of workflow {self.workflow_id}'


class AuditLog(models.Model):
    """Append-only activity log. Rows are never edited or deleted — see
    the immutability guards below and the DB-level triggers added in
    migration 0006 (core_auditlog_block_mutation), which reject any
    UPDATE/DELETE even if something bypasses the ORM (bulk queries, the
    admin, raw SQL)."""

    class Action(models.TextChoices):
        CREATE = 'create', 'Create'
        UPDATE = 'update', 'Update'
        DELETE = 'delete', 'Delete'
        APPROVE = 'approve', 'Approve'
        REJECT = 'reject', 'Reject'
        LOGIN = 'login', 'Login'
        LOGIN_FAILED = 'login_failed', 'Failed login'
        SIGNATURE_FAILED = 'signature_failed', 'Failed signature attempt'

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    target = GenericForeignKey('content_type', 'object_id')
    target_repr = models.CharField(
        max_length=255, blank=True, help_text='str() of the target at log time, in case it is later deleted',
    )
    metadata = models.JSONField(blank=True, default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.actor} {self.action} {self.target_repr} at {self.created_at}'

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError('AuditLog entries are immutable and cannot be edited.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError('AuditLog entries are immutable and cannot be deleted.')


class ElectronicSignature(models.Model):
    """A 21 CFR Part 11 electronic signature (§11.50, §11.70, §11.100,
    §11.200): a deliberate, re-authenticated act binding one specific
    person, a stated meaning, and a timestamp to one specific record.

    Created only by WorkflowStepViewSet.decide(), and only after
    verifying the signer's password at the moment of signing — being
    already logged in (a valid token/session) is deliberately NOT
    sufficient on its own, per §11.200(a)(1)'s "at least two distinct
    identification components" requirement.

    Immutable for the same reason as AuditLog (see save()/delete() below
    and the DB trigger in migration 0012): a signature record that could
    be edited or deleted after the fact isn't a signature. See also
    integrity_hash — §11.70 requires signatures be linked to their record
    so they can't be excised, copied, or transferred to falsify a
    different one; the hash makes such tampering detectable.
    """

    class Meaning(models.TextChoices):
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        REVIEWED = 'reviewed', 'Reviewed'
        AUTHORED = 'authored', 'Authored'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    # A snapshot, not just the FK: §11.50(a)(1) signature manifestations
    # must show the printed name of the signer as it was AT SIGNING TIME,
    # not whatever the account's name happens to be if it's changed since.
    printed_name = models.CharField(max_length=255)
    meaning = models.CharField(max_length=20, choices=Meaning.choices)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    target = GenericForeignKey('content_type', 'object_id')
    target_repr = models.CharField(max_length=255, blank=True)
    integrity_hash = models.CharField(max_length=64, editable=False)
    signed_at = models.DateTimeField()

    class Meta:
        ordering = ['-signed_at']

    def __str__(self):
        return f'{self.printed_name} {self.meaning} {self.target_repr} at {self.signed_at}'

    def compute_hash(self):
        import hashlib
        payload = '|'.join(str(p) for p in (
            self.user_id, self.printed_name, self.meaning,
            self.content_type_id, self.object_id, self.signed_at.isoformat(), settings.SECRET_KEY,
        ))
        return hashlib.sha256(payload.encode()).hexdigest()

    def verify(self):
        """True if this row hasn't been tampered with since signing."""
        return self.integrity_hash == self.compute_hash()

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError('ElectronicSignature entries are immutable and cannot be edited.')
        if not self.signed_at:
            from django.utils import timezone
            self.signed_at = timezone.now()
        if not self.integrity_hash:
            self.integrity_hash = self.compute_hash()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError('ElectronicSignature entries are immutable and cannot be deleted.')
