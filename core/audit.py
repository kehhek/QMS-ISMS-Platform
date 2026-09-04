"""Shared helper for writing AuditLog entries from any app. AuditLog
itself lives in core (a TENANT_APPS model), but auth events and tenant
settings/membership changes happen in accounts/ and tenants/ — this
avoids duplicating the ContentType lookup in three places."""


def log_action(actor, action, target, metadata=None):
    from django.contrib.contenttypes.models import ContentType
    from .models import AuditLog

    AuditLog.objects.create(
        actor=actor if getattr(actor, 'is_authenticated', False) else None,
        action=action,
        content_type=ContentType.objects.get_for_model(target),
        object_id=target.pk,
        target_repr=str(target),
        metadata=metadata or {},
    )
