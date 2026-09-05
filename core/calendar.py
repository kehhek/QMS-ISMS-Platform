"""Shared ISMS Calendar logic — the same overdue/upcoming computation
backs both IsmsCalendarView (core/views.py, for the console UI) and the
send_overdue_isms_digest Celery task (core/tasks.py, for email). Kept in
one place so the two can never quietly drift out of sync with each other."""

from django.utils import timezone

from .models import Audit, CorrectiveAction, Risk, TrainingRecord, CalendarEvent


def get_isms_calendar_events(today=None):
    """Every ISMS date that matters in the CURRENT schema, split into
    overdue (past due, not yet closed/completed) and upcoming (due today
    or later), each sorted soonest-first. Caller is responsible for being
    in the right tenant schema_context first."""
    today = today or timezone.localdate()
    events = []

    for audit in Audit.objects.exclude(status__in=[Audit.Status.COMPLETED, Audit.Status.CANCELLED]):
        if audit.scheduled_date:
            events.append({
                'kind': 'audit', 'id': audit.id, 'title': audit.title,
                'date': audit.scheduled_date, 'status': audit.status,
            })

    for capa in CorrectiveAction.objects.exclude(status=CorrectiveAction.Status.CLOSED):
        if capa.due_date:
            events.append({
                'kind': 'corrective_action', 'id': capa.id, 'title': capa.title,
                'date': capa.due_date, 'status': capa.status,
            })

    for risk in Risk.objects.exclude(status=Risk.Status.CLOSED):
        if risk.target_date:
            events.append({
                'kind': 'risk', 'id': risk.id, 'title': risk.name,
                'date': risk.target_date, 'status': risk.status,
            })

    for training in TrainingRecord.objects.exclude(status=TrainingRecord.Status.COMPLETED).select_related('user'):
        if training.due_date:
            events.append({
                'kind': 'training', 'id': training.id,
                'title': f'{training.title} — {training.user.username}',
                'date': training.due_date, 'status': training.status,
            })

    for custom in CalendarEvent.objects.all():
        events.append({
            'kind': 'custom', 'id': custom.id, 'title': custom.title,
            'date': custom.date, 'status': '',
        })

    overdue = sorted((e for e in events if e['date'] < today), key=lambda e: e['date'])
    upcoming = sorted((e for e in events if e['date'] >= today), key=lambda e: e['date'])
    return overdue, upcoming
