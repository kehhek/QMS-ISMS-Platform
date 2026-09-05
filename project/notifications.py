"""Thin, best-effort email wrapper used across apps (accounts, tenants,
core) — kept here rather than in any one app to avoid a cross-app import
just for something this small. Every call site treats a send as
best-effort: a broken SMTP config in production shouldn't turn into a
500 on "invite a member" or "submit a demo request"."""

import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def send_notification_email(subject, message, recipient_list):
    """Send a plain-text email; return True/False rather than raising.
    Failures are logged so they're visible in the container's logs (or,
    in DEBUG, every email is also printed to stdout by the console
    backend regardless of success)."""
    recipient_list = [r for r in (recipient_list or []) if r]
    if not recipient_list:
        return False
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient_list, fail_silently=False)
        return True
    except Exception:
        logger.exception('Failed to send notification email %r to %r', subject, recipient_list)
        return False
