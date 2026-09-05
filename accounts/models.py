from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class User(AbstractUser):
    """Extends Django's user with the account-security state 21 CFR Part 11
    §11.300 calls for: periodic password revision (§11.300(b)) and a
    transaction safeguard against repeated unauthorized-access attempts
    (§11.300(d)). See accounts/security.py for where these are enforced."""

    password_changed_at = models.DateTimeField(default=timezone.now)
    failed_login_count = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    def set_password(self, raw_password):
        super().set_password(raw_password)
        self.password_changed_at = timezone.now()

    def is_locked(self):
        return bool(self.locked_until and self.locked_until > timezone.now())

    def password_expired(self, max_age_days):
        if not max_age_days:
            return False
        return timezone.now() - self.password_changed_at > timezone.timedelta(days=max_age_days)
