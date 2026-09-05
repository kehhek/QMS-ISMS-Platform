from django.contrib.auth import get_user_model
from django.db import connection
from rest_framework import viewsets, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from core.audit import log_action
from core.models import AuditLog
from project.notifications import send_notification_email
from tenants.permissions import HasTenantRole
from tenants.utils import generate_password

from .models import Membership, DemoRequest
from .serializers import (
    TenantSettingsSerializer, MembershipSerializer, MembershipInviteSerializer, DemoRequestSerializer,
)

User = get_user_model()


def _current_tenant():
    return getattr(connection, 'tenant', None)


class TenantSettingsView(APIView):
    """View/update the current tenant's org branding & info. Scoped to
    whichever tenant the request's Host header resolved to."""

    permission_classes = [HasTenantRole]
    allowed_roles = ['admin']

    def get(self, request):
        tenant = _current_tenant()
        if tenant is None:
            return Response({'detail': 'No active tenant for this request.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(TenantSettingsSerializer(tenant).data)

    def patch(self, request):
        tenant = _current_tenant()
        if tenant is None:
            return Response({'detail': 'No active tenant for this request.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = TenantSettingsSerializer(tenant, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_action(request.user, AuditLog.Action.UPDATE, tenant, metadata={'fields': list(request.data.keys())})
        return Response(serializer.data)


class DemoRequestView(APIView):
    """Public "Request a demo" form on the home page — unauthenticated,
    like RegisterView, and for the same reason: there's no user yet to
    authenticate as. Unlike RegisterView, this doesn't create a tenant or
    an account at all, just a lead for a human to follow up on, so it
    doesn't need connection.set_schema_to_public() — DemoRequest is a
    SHARED_APP model, reachable (and written) the same way regardless of
    which tenant's schema happens to be active on the connection."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'demo-request'

    def post(self, request):
        from django.conf import settings

        serializer = DemoRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        demo_request = serializer.save()

        # Best-effort — a demo request still lands in Django admin even
        # if this fails or DEMO_REQUEST_NOTIFY_EMAIL isn't set; it just
        # won't page anyone.
        send_notification_email(
            subject=f'New demo request: {demo_request.name} ({demo_request.company or "no company given"})',
            message=(
                f'Name: {demo_request.name}\n'
                f'Email: {demo_request.email}\n'
                f'Company: {demo_request.company or "—"}\n\n'
                f'Message:\n{demo_request.message or "(none)"}'
            ),
            recipient_list=[settings.DEMO_REQUEST_NOTIFY_EMAIL],
        )
        return Response({'ok': True}, status=status.HTTP_201_CREATED)


class MembershipViewSet(viewsets.ModelViewSet):
    """Manage who belongs to the current tenant and what role they have.
    Scoped to the current tenant only — there is no cross-tenant listing."""

    serializer_class = MembershipSerializer
    permission_classes = [HasTenantRole]
    allowed_roles = ['admin']

    def get_queryset(self):
        tenant = _current_tenant()
        if tenant is None:
            return Membership.objects.none()
        return Membership.objects.filter(tenant=tenant).select_related('user')

    def create(self, request, *args, **kwargs):
        """Add an existing user (by username) or invite a brand-new one to
        this tenant with a role. New users get a generated password —
        emailed to them if an email was given (best-effort; see
        project.notifications), and always also returned once in the
        response so an admin can relay it out of band if email isn't
        configured or the address bounces."""
        tenant = _current_tenant()
        if tenant is None:
            return Response({'detail': 'No active tenant for this request.'}, status=status.HTTP_404_NOT_FOUND)

        invite = MembershipInviteSerializer(data=request.data)
        invite.is_valid(raise_exception=True)
        data = invite.validated_data

        user, user_created = User.objects.get_or_create(
            username=data['username'],
            defaults={'email': data.get('email', '')},
        )
        generated_password = None
        email_sent = False
        if user_created:
            generated_password = generate_password()
            user.set_password(generated_password)
            user.save()
            if user.email:
                email_sent = send_notification_email(
                    subject=f'You have been invited to {tenant.name}',
                    message=(
                        f'You have been added to {tenant.name} as a {data["role"]}.\n\n'
                        f'Username: {user.username}\n'
                        f'Temporary password: {generated_password}\n\n'
                        'Log in and change your password as soon as possible.'
                    ),
                    recipient_list=[user.email],
                )

        membership, membership_created = Membership.objects.update_or_create(
            user=user, tenant=tenant, defaults={'role': data['role']},
        )
        log_action(
            request.user,
            AuditLog.Action.CREATE if membership_created else AuditLog.Action.UPDATE,
            membership,
            metadata={'username': user.username, 'role': data['role'], 'new_user': user_created},
        )
        payload = MembershipSerializer(membership).data
        if generated_password:
            payload['generated_password'] = generated_password
            payload['invite_email_sent'] = email_sent
        return Response(
            payload,
            status=status.HTTP_201_CREATED if membership_created else status.HTTP_200_OK,
        )
