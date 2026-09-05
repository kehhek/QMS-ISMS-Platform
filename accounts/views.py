from django.conf import settings
from django.core.management import call_command
from django.db import connection

from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.response import Response
from rest_framework import status
from tenants.models import Client, Domain, Membership
from tenants.utils import generate_password
from django_tenants.utils import schema_context
from django.contrib.auth import get_user_model, login, logout, authenticate
from core.audit import log_action
from core.models import AuditLog
from project.notifications import send_notification_email
from .serializers import (
    TenantOnboardSerializer, RegisterSerializer, ChangePasswordSerializer, ExpiredPasswordChangeSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer,
)
from .security import check_lockout, record_failed_login, record_successful_login
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.views import APIView
from rest_framework.decorators import authentication_classes


def seed_control_catalog(schema_name):
    """Load the full ISO 27001 + SOC 2 control catalog into a freshly
    created tenant schema. Idempotent (get_or_create keyed on
    framework+identifier), so it's safe to call again if this is ever
    re-run for an existing schema."""
    call_command('seed_control_catalogs', schema=[schema_name])


@api_view(['POST'])
@permission_classes([IsAdminUser])
def onboard_tenant(request):
    """Endpoint to create a tenant from the public schema. Provisioning a
    brand-new tenant is a platform-operator action, not something any
    tenant admin should be able to trigger — gated on is_superuser, not
    just is_staff/IsAdminUser, since IsAdminUser alone would (before this
    fix, did) let a tenant's own admin call this for themselves."""
    if not request.user.is_superuser:
        return Response(
            {'detail': 'Only a platform superuser can provision a new tenant.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = TenantOnboardSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    # Tenant creation requires the connection to be on the public schema —
    # force it explicitly rather than depending on this request having
    # arrived via some specific "platform" domain.
    connection.set_schema_to_public()

    branding_fields = {
        k: data[k] for k in ('logo_url', 'primary_color', 'support_email', 'website') if k in data
    }
    client = Client(schema_name=data['schema'], name=data['name'], **branding_fields)
    client.save()
    Domain.objects.create(domain=data['domain'], tenant=client, is_primary=True)

    password = data.get('admin_password') or generate_password()
    password_was_generated = not data.get('admin_password')

    # create admin user inside tenant schema
    with schema_context(client.schema_name):
        User = get_user_model()
        # Deliberately NOT is_superuser/is_staff: accounts.User is a
        # SHARED_APP model, so those flags are GLOBAL, not scoped to this
        # tenant. Setting them here used to make every tenant's own admin
        # a platform-wide Django superuser — able to log into /admin/ and
        # read/edit every OTHER tenant's users, domains, and memberships.
        # This tenant's "admin" role is fully and correctly conveyed by
        # the Membership row below, which HasTenantRole scopes per-tenant.
        user, created = User.objects.get_or_create(
            username=data['admin_username'],
            defaults={'email': data['admin_email']},
        )
        if created:
            user.set_password(password)
            user.save()
        Membership.objects.get_or_create(user=user, tenant=client, defaults={'role': Membership.Role.ADMIN})
        seed_control_catalog(client.schema_name)

    response = {'ok': True, 'schema': client.schema_name}
    if password_was_generated:
        response['generated_admin_password'] = password
    return Response(response, status=status.HTTP_201_CREATED)


class RegisterView(APIView):
    """Public self-service signup — the "Get started" flow off the home
    page's pricing section. Unlike onboard_tenant (platform-admin-only,
    for provisioning a tenant on someone else's behalf), this creates a
    brand-new tenant AND its first admin user in one unauthenticated call,
    then returns a token so the frontend can log the user straight into
    their new tenant's dashboard.

    authentication_classes = [] for the same reason as the token-obtain
    view: this must never depend on already having a session, and it's
    also the entry point that CAN'T be authenticated as anyone yet.
    Rate-limited harder than general anonymous traffic (a fresh Postgres
    schema per call is a much heavier operation than a normal API read).
    """

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'registration'

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        slug = data['subdomain']
        schema_name = f"org_{slug.replace('-', '_')}"
        domain_name = f'{slug}.localhost'

        # Tenant creation requires the connection to be on the public
        # schema — force it explicitly rather than depending on which
        # domain routed this request here (there's no tenant yet for a
        # brand-new signup, so this can't depend on tenant routing at all).
        connection.set_schema_to_public()

        client = Client.objects.create(schema_name=schema_name, name=data['org_name'], plan=data['plan'])
        Domain.objects.create(domain=domain_name, tenant=client, is_primary=True)

        if settings.DEBUG:
            # Local-dev convenience only, mirroring the same fix used for
            # the CSRF issue and the frontend proxy: the dev frontend's
            # proxy always talks to ONE fixed backend host
            # (host.docker.internal), so re-point that (and bare
            # localhost) at whichever tenant most recently registered —
            # otherwise "land on the dashboard" would show someone else's
            # tenant. A real deployment gives each tenant its own real
            # subdomain via wildcard DNS and never needs this.
            for dev_domain in ('host.docker.internal', 'localhost'):
                Domain.objects.update_or_create(domain=dev_domain, defaults={'tenant': client, 'is_primary': False})

        with schema_context(client.schema_name):
            User = get_user_model()
            # Deliberately NOT is_superuser/is_staff — see the identical
            # comment in onboard_tenant. accounts.User is a SHARED_APP
            # model, so those flags are platform-global: granting them
            # here used to make every self-registered tenant's founder a
            # Django superuser who could log into /admin/ and read/edit
            # every OTHER tenant's users, domains, and memberships. The
            # Membership row below is the correct, tenant-scoped way to
            # grant this user the admin role for THEIR tenant only.
            user = User.objects.create_user(
                username=data['username'], email=data['email'], password=data['password'],
            )
            Membership.objects.create(user=user, tenant=client, role=Membership.Role.ADMIN)
            token, _ = Token.objects.get_or_create(user=user)
            log_action(user, AuditLog.Action.LOGIN, user, metadata={'method': 'registration'})

            # Every tenant should start with the full ISO 27001 + SOC 2
            # control catalog already loaded — nobody should have to know
            # to run a management command by hand just to see the Controls
            # page populated. Seeded inside this schema_context so it lands
            # in the brand-new tenant's own schema, not whichever one the
            # request happened to route through.
            seed_control_catalog(client.schema_name)

        return Response({
            'ok': True,
            'token': token.key,
            'schema': client.schema_name,
            'domain': domain_name,
            'username': user.username,
        }, status=status.HTTP_201_CREATED)


class LoggingObtainAuthToken(ObtainAuthToken):
    """Same as DRF's stock token-obtain view, but records every attempt
    (success or failure) in the audit log — this is the primary login
    path in practice, since the frontend and every curl example in this
    project use token auth rather than session login.

    authentication_classes = [] is deliberate, not an oversight: this is
    the "give me credentials to use everywhere else" endpoint, so it must
    never depend on already having a session. Without this, a leftover
    Django admin session cookie in the same browser (admin and the
    frontend share the plain hostname `localhost`, and cookies aren't
    port-scoped) makes DRF's SessionAuthentication kick in on this exact
    request — which has no Authorization header yet, since obtaining one
    is the whole point — and its CSRF check then rejects a plain JSON
    POST with "CSRF Failed: CSRF token missing." Reproduced directly
    against this endpoint before this fix; confirmed gone after."""

    authentication_classes = []

    def post(self, request, *args, **kwargs):
        username = request.data.get('username', '')
        existing_user = get_user_model().objects.filter(username=username).first()

        # Part 11 §11.300(d): reject before even checking the password once
        # locked, rather than after — this also avoids leaking whether a
        # locked account's submitted password would otherwise be correct.
        if existing_user:
            lockout_message = check_lockout(existing_user)
            if lockout_message:
                log_action(
                    None, AuditLog.Action.LOGIN_FAILED, existing_user,
                    metadata={'method': 'token', 'reason': 'locked'},
                )
                return Response({'detail': lockout_message}, status=status.HTTP_403_FORBIDDEN)

        serializer = self.serializer_class(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.validated_data['user']

            # Part 11 §11.300(b): periodic password revision. The password
            # itself was correct — record the successful auth attempt as
            # such (resets the lockout counter) but withhold the token
            # until they set a new one via ExpiredPasswordChangeView,
            # which re-verifies the same credentials.
            if user.password_expired(settings.PART11_PASSWORD_MAX_AGE_DAYS):
                record_successful_login(user)
                log_action(user, AuditLog.Action.LOGIN_FAILED, user, metadata={'method': 'token', 'reason': 'password_expired'})
                return Response(
                    {'detail': 'Your password has expired and must be changed.', 'password_expired': True},
                    status=status.HTTP_403_FORBIDDEN,
                )

            record_successful_login(user)
            token, _ = Token.objects.get_or_create(user=user)
            log_action(user, AuditLog.Action.LOGIN, user, metadata={'method': 'token'})
            return Response({'token': token.key})

        if existing_user:
            record_failed_login(existing_user)
            log_action(None, AuditLog.Action.LOGIN_FAILED, existing_user, metadata={'method': 'token'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        existing_user = get_user_model().objects.filter(username=username).first()

        if existing_user:
            lockout_message = check_lockout(existing_user)
            if lockout_message:
                log_action(
                    None, AuditLog.Action.LOGIN_FAILED, existing_user,
                    metadata={'method': 'session', 'reason': 'locked'},
                )
                return Response({'detail': lockout_message}, status=status.HTTP_403_FORBIDDEN)

        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_active:
            if user.password_expired(settings.PART11_PASSWORD_MAX_AGE_DAYS):
                record_successful_login(user)
                log_action(user, AuditLog.Action.LOGIN_FAILED, user, metadata={'method': 'session', 'reason': 'password_expired'})
                return Response(
                    {'detail': 'Your password has expired and must be changed.', 'password_expired': True},
                    status=status.HTTP_403_FORBIDDEN,
                )

            record_successful_login(user)
            login(request, user)
            log_action(user, AuditLog.Action.LOGIN, user, metadata={'method': 'session'})
            return Response({'ok': True, 'username': user.username})

        if existing_user:
            record_failed_login(existing_user)
            log_action(None, AuditLog.Action.LOGIN_FAILED, existing_user, metadata={'method': 'session'})
        return Response({'ok': False}, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    authentication_classes = [SessionAuthentication]

    def post(self, request):
        logout(request)
        return Response({'ok': True})


class ChangePasswordView(APIView):
    """A logged-in user changing their own password by choice — not the
    expired-password flow (ExpiredPasswordChangeView below), which is
    for someone who can't get a token at all yet."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer._password_validation_user = request.user
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if not request.user.check_password(data['old_password']):
            return Response({'old_password': ['Incorrect password.']}, status=status.HTTP_400_BAD_REQUEST)

        request.user.set_password(data['new_password'])
        request.user.save()
        log_action(request.user, AuditLog.Action.PASSWORD_CHANGED, request.user)
        return Response({'ok': True})


class ExpiredPasswordChangeView(APIView):
    """Part 11 §11.300(b): the self-service escape hatch for someone
    LoggingObtainAuthToken/LoginView just refused to log in because
    password_expired() is true. Re-verifies username+old password (the
    same two things a login would check) rather than trusting the
    username alone, then issues a token exactly like a successful login
    would — so the frontend can go straight from "expired" to "logged in
    with the new password" in one step.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ExpiredPasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        User = get_user_model()
        user = User.objects.filter(username=data['username']).first()

        lockout_message = user and check_lockout(user)
        if lockout_message:
            log_action(None, AuditLog.Action.LOGIN_FAILED, user, metadata={'method': 'password_change', 'reason': 'locked'})
            return Response({'detail': lockout_message}, status=status.HTTP_403_FORBIDDEN)

        if not user or not user.check_password(data['old_password']):
            if user:
                record_failed_login(user)
                log_action(None, AuditLog.Action.LOGIN_FAILED, user, metadata={'method': 'password_change'})
            return Response({'detail': 'Incorrect username or password.'}, status=status.HTTP_400_BAD_REQUEST)

        record_successful_login(user)
        user.set_password(data['new_password'])
        user.save()
        log_action(user, AuditLog.Action.PASSWORD_CHANGED, user, metadata={'reason': 'expired'})

        token, _ = Token.objects.get_or_create(user=user)
        log_action(user, AuditLog.Action.LOGIN, user, metadata={'method': 'token', 'after': 'password_change'})
        return Response({'token': token.key})


class PasswordResetRequestView(APIView):
    """"Forgot password" step 1: email a reset link. Always returns the
    same generic response whether or not the username exists or has an
    email on file — the response itself must never leak that, or this
    becomes a username-enumeration oracle."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'password-reset'

    GENERIC_RESPONSE = {
        'ok': True,
        'detail': 'If an account with that username exists and has an email on file, a reset link has been sent.',
    }

    def post(self, request):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = get_user_model().objects.filter(username=serializer.validated_data['username']).first()
        if user and user.email:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_path = f'/reset-password?uid={uid}&token={token}'
            # FRONTEND_BASE_URL (set it in production — see settings.py)
            # points at wherever the React app is actually served; in dev,
            # where frontend/backend run on different ports, falling back
            # to the request's own origin gives a real, working link, just
            # one that lands on the Django origin rather than :3001.
            base_url = settings.FRONTEND_BASE_URL or request.build_absolute_uri('/').rstrip('/')
            send_notification_email(
                subject='Reset your password',
                message=(
                    f'Someone (hopefully you) requested a password reset for {user.username}.\n\n'
                    f'Open this link to set a new password: {base_url}{reset_path}\n\n'
                    'If you did not request this, you can ignore this email — your password will not change.'
                ),
                recipient_list=[user.email],
            )
            log_action(None, AuditLog.Action.LOGIN_FAILED, user, metadata={'method': 'password_reset_requested'})

        return Response(self.GENERIC_RESPONSE)


class PasswordResetConfirmView(APIView):
    """"Forgot password" step 2: the link from the email. uid+token
    together prove "you received this email", which is the whole point —
    no old password needed, unlike ExpiredPasswordChangeView."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'password-reset'

    def post(self, request):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_str
        from django.utils.http import urlsafe_base64_decode

        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        User = get_user_model()
        try:
            uid = force_str(urlsafe_base64_decode(data['uid']))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is None or not default_token_generator.check_token(user, data['token']):
            return Response({'detail': 'This reset link is invalid or has expired.'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(data['new_password'])
        user.save()
        log_action(user, AuditLog.Action.PASSWORD_CHANGED, user, metadata={'reason': 'reset_link'})

        token, _ = Token.objects.get_or_create(user=user)
        log_action(user, AuditLog.Action.LOGIN, user, metadata={'method': 'token', 'after': 'password_reset'})
        return Response({'token': token.key})


# UserViewSet/GroupViewSet used to live here: a full ModelViewSet over
# EVERY user and Django Group platform-wide, gated only by IsAdminUser
# (is_staff) — which, combined with RegisterView/onboard_tenant granting
# is_staff to every tenant's own admin, let any tenant's admin list,
# edit, and delete every OTHER tenant's users. Removed rather than
# re-scoped: nothing in this product needs cross-tenant user/group
# management via the API, and auth.Group itself is vestigial — per-tenant
# roles are Membership.role, not Django Groups (see tenants/permissions.py).
