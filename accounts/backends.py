from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from .security import check_lockout, record_failed_login, record_successful_login

User = get_user_model()


class Part11LockoutBackend(ModelBackend):
    """Wraps ModelBackend so the 21 CFR Part 11 §11.300(d) account-lockout
    enforcement applies to every login path that goes through Django's
    `authenticate()` — not just the two custom API login views
    (LoggingObtainAuthToken/LoginView) that used to call
    check_lockout/record_*_login by hand. That previously left Django
    admin's own /admin/login/ with no lockout protection at all: it
    authenticates via the default ModelBackend, which knows nothing
    about failed_login_count/locked_until.

    This is now the single place those fields actually get updated —
    LoggingObtainAuthToken/LoginView no longer call record_failed_login/
    record_successful_login themselves (both already route through
    authenticate() one way or another, so doing it in both places would
    double-count). They still call check_lockout up front on their own,
    purely to return a nicer, distinguishable "locked out" message
    before touching the password at all — something this backend can't
    do, since authenticate() has no access to the view's response.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        try:
            user = User._default_manager.get_by_natural_key(username)
        except User.DoesNotExist:
            # Same timing-attack mitigation as ModelBackend itself: run
            # the password hasher anyway so a nonexistent username
            # doesn't respond measurably faster than a real one.
            User().set_password(password)
            return None

        if check_lockout(user):
            return None

        if self.user_can_authenticate(user) and user.check_password(password):
            record_successful_login(user)
            return user

        record_failed_login(user)
        return None
