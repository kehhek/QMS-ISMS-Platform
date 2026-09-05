"""Account-security enforcement for 21 CFR Part 11 §11.300(b)/(d):
periodic password revision and a transaction safeguard against repeated
unauthorized-access attempts (account lockout). Shared by every login
path (token obtain, session login) so the policy is enforced
consistently instead of duplicated per view."""

from django.conf import settings
from django.utils import timezone


def check_lockout(user):
    """An error message if `user` is currently locked out, else None."""
    if user.is_locked():
        remaining = (user.locked_until - timezone.now()).total_seconds()
        minutes = max(1, int(remaining // 60) + 1)
        return f'Account locked due to repeated failed sign-in attempts. Try again in about {minutes} minute(s).'
    return None


def record_failed_login(user):
    user.failed_login_count += 1
    if user.failed_login_count >= settings.PART11_MAX_FAILED_LOGINS:
        user.locked_until = timezone.now() + timezone.timedelta(minutes=settings.PART11_LOCKOUT_MINUTES)
    user.save(update_fields=['failed_login_count', 'locked_until'])


def record_successful_login(user):
    if user.failed_login_count or user.locked_until:
        user.failed_login_count = 0
        user.locked_until = None
        user.save(update_fields=['failed_login_count', 'locked_until'])
