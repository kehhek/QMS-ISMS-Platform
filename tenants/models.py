from django.conf import settings
from django.db import models
from django_tenants.models import TenantMixin, DomainMixin


class Client(TenantMixin):
    class Plan(models.TextChoices):
        FREE = 'free', 'Free'
        TEAM = 'team', 'Team'
        ENTERPRISE = 'enterprise', 'Enterprise'

    name = models.CharField(max_length=100)
    plan = models.CharField(max_length=20, choices=Plan.choices, default=Plan.FREE)
    paid_until = models.DateField(null=True, blank=True)
    on_trial = models.BooleanField(default=True)
    created_on = models.DateField(auto_now_add=True)

    # Org branding / info, shown in the tenant's admin UI and (eventually)
    # on exported reports.
    logo_url = models.URLField(blank=True)
    primary_color = models.CharField(max_length=7, blank=True, help_text='Hex color, e.g. #4f46e5')
    support_email = models.EmailField(blank=True)
    website = models.URLField(blank=True)

    # default true means create schema when saving tenant
    auto_create_schema = True

    def __str__(self):
        return self.name


class Domain(DomainMixin):
    pass


class Membership(models.Model):
    """A user's role within a specific tenant.

    accounts.User and tenants.Client both live in the shared/public
    schema, so this join table does too — it's the source of truth for
    "what can this user do in this org", independent of which tenant
    schema is currently active on the connection.
    """

    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        AUDITOR = 'auditor', 'Auditor'
        USER = 'user', 'User'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='memberships')
    tenant = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'tenant')
        ordering = ['tenant', 'role']

    def __str__(self):
        return f'{self.user} @ {self.tenant} ({self.role})'


class DemoRequest(models.Model):
    """A lead captured from the public home page's "Request a demo" form.
    Distinct from RegisterView's self-service signup — this doesn't
    create a tenant or an account, just a note for sales/support to
    follow up on. Lives in the public schema (tenants is a SHARED_APP):
    a demo request isn't scoped to any one tenant, and reachable from any
    schema's search_path the same way User/Client/Membership already
    are."""

    class Status(models.TextChoices):
        NEW = 'new', 'New'
        CONTACTED = 'contacted', 'Contacted'
        CONVERTED = 'converted', 'Converted'
        DECLINED = 'declined', 'Declined'

    name = models.CharField(max_length=255)
    email = models.EmailField()
    company = models.CharField(max_length=255, blank=True)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.email})'
