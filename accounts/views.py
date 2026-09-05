from django.conf import settings
from django.db import connection

from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.response import Response
from rest_framework import status, viewsets
from tenants.models import Client, Domain, Membership
from tenants.utils import generate_password
from django_tenants.utils import schema_context
from django.contrib.auth import get_user_model, login, logout, authenticate
from django.contrib.auth.models import Group
from core.audit import log_action
from core.models import AuditLog
from .serializers import TenantOnboardSerializer, RegisterSerializer, UserSerializer, GroupSerializer
from .security import check_lockout, record_failed_login, record_successful_login
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.views import APIView
from rest_framework.decorators import authentication_classes


@api_view(['POST'])
@permission_classes([IsAdminUser])
def onboard_tenant(request):
    """Endpoint to create a tenant from the public schema. Must be called from public and by an admin."""
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
        user, created = User.objects.get_or_create(
            username=data['admin_username'],
            defaults={'email': data['admin_email'], 'is_superuser': True, 'is_staff': True},
        )
        if created:
            user.set_password(password)
            user.save()
        Membership.objects.get_or_create(user=user, tenant=client, defaults={'role': Membership.Role.ADMIN})

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
            user = User.objects.create_user(
                username=data['username'], email=data['email'], password=data['password'],
                is_superuser=True, is_staff=True,
            )
            Membership.objects.create(user=user, tenant=client, role=Membership.Role.ADMIN)
            token, _ = Token.objects.get_or_create(user=user)
            log_action(user, AuditLog.Action.LOGIN, user, metadata={'method': 'registration'})

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


class UserViewSet(viewsets.ModelViewSet):
    queryset = get_user_model().objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsAdminUser]
