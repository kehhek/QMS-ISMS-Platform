import logging

from django.db import connection
from django_tenants.utils import get_tenant_model, schema_context

from project.celery import app
from project.notifications import send_notification_email

logger = logging.getLogger(__name__)


@app.task
def send_overdue_isms_digest():
    """Scans every tenant for overdue ISMS Calendar items (audits, CAPAs,
    risk treatments, security awareness training — see core/calendar.py)
    and emails a digest to that tenant's admins/auditors. Runs daily
    (project/settings.py CELERY_BEAT_SCHEDULE) — replaces the old
    'run-audit-every-minute' placeholder, which just printed a string and
    did nothing real.

    Best-effort per tenant: one tenant's email failure or data issue
    doesn't stop the others from being processed.
    """
    from .calendar import get_isms_calendar_events
    from tenants.models import Membership

    Client = get_tenant_model()
    sent_count = 0

    for schema_name in Client.objects.exclude(schema_name='public').values_list('schema_name', flat=True):
        try:
            with schema_context(schema_name):
                overdue, _upcoming = get_isms_calendar_events()
                if not overdue:
                    continue

                recipients = list(
                    Membership.objects.filter(tenant__schema_name=schema_name, role__in=['admin', 'auditor'])
                    .select_related('user')
                    .values_list('user__email', flat=True)
                )
                recipients = [r for r in recipients if r]
                if not recipients:
                    continue

                lines = [f"{len(overdue)} ISMS item(s) are now past due:", '']
                for event in overdue[:20]:
                    lines.append(f"- [{event['kind']}] {event['title']} — was due {event['date']}")
                if len(overdue) > 20:
                    lines.append(f'...and {len(overdue) - 20} more.')

                if send_notification_email(
                    subject=f'{len(overdue)} overdue ISMS item(s) need attention',
                    message='\n'.join(lines),
                    recipient_list=recipients,
                ):
                    sent_count += 1
        except Exception:
            logger.exception('send_overdue_isms_digest failed for schema %s', schema_name)
        finally:
            connection.set_schema_to_public()

    return sent_count
