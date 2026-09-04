from django.contrib.auth import get_user_model
from django.db import connection
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.audit import log_action
from core.models import AuditLog
from tenants.permissions import HasTenantRole
from tenants.utils import generate_password

from .models import Membership
from .serializers import TenantSettingsSerializer, MembershipSerializer, MembershipInviteSerializer

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
        this tenant with a role. New users get a generated password,
        returned once in the response (there's no email/invite delivery
        yet — an admin has to relay it out of band)."""
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
        if user_created:
            generated_password = generate_password()
            user.set_password(generated_password)
            user.save()

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
        return Response(
            payload,
            status=status.HTTP_201_CREATED if membership_created else status.HTTP_200_OK,
        )
