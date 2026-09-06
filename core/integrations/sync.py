"""Runs one Integration's checks and applies the results — the one place
"a provider outcome becomes a real Control status + Evidence row" logic
lives, so every provider gets it for free instead of reimplementing it."""
from django.utils import timezone

from .base import IntegrationError
from .registry import get_provider


def sync_integration(integration, actor=None):
    """Returns the list of IntegrationCheckResult rows created. Raises
    IntegrationError (after recording it on the Integration itself) if
    the provider couldn't complete the sync at all — a single check
    failing its assertion is NOT an error here, that's just `passed=False`
    and a Control correctly marked not-implemented."""
    from django.contrib.contenttypes.models import ContentType
    from core.models import Control, Evidence, IntegrationCheckResult

    provider = get_provider(integration.provider)
    credentials = integration.get_credentials()

    try:
        outcomes = provider.run_checks(credentials, integration.config)
    except IntegrationError as exc:
        integration.status = integration.Status.ERROR
        integration.last_error = str(exc)
        integration.last_synced_at = timezone.now()
        integration.save(update_fields=['status', 'last_error', 'last_synced_at'])
        raise

    control_ct = ContentType.objects.get_for_model(Control)
    results = []
    for outcome in outcomes:
        control = Control.objects.filter(
            framework=outcome.control_framework, identifier=outcome.control_identifier,
        ).first()
        if control:
            control.status = Control.Status.IMPLEMENTED if outcome.passed else Control.Status.NOT_IMPLEMENTED
            control.save(update_fields=['status'])
            # A fresh Evidence row every sync — not one row silently
            # overwritten — so a control's real compliance history is
            # visible, the same "dated trail, not a snapshot" reasoning
            # as IntegrationCheckResult itself.
            Evidence.objects.create(
                title=f'{outcome.label} ({"PASS" if outcome.passed else "FAIL"}) — automated check',
                description=outcome.detail,
                uploaded_by=actor,
                content_type=control_ct, object_id=control.id,
            )
        results.append(IntegrationCheckResult.objects.create(
            integration=integration, control=control, check_key=outcome.key,
            label=outcome.label, passed=outcome.passed, detail=outcome.detail,
        ))

    integration.status = integration.Status.CONNECTED
    integration.last_error = ''
    integration.last_synced_at = timezone.now()
    integration.save(update_fields=['status', 'last_error', 'last_synced_at'])
    return results
