from django.contrib.auth import get_user_model
from django.db import connection
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from core.audit import log_action
from core.export import CsvExportMixin
from core.models import AuditLog
from project.notifications import send_notification_email
from tenants.permissions import HasTenantRole, HasTenantRoleStrict
from tenants.utils import generate_password

from .models import Membership, DemoRequest, AccessReview, UserGroup, UserGroupMember
from .serializers import (
    TenantSettingsSerializer, MembershipSerializer, MembershipInviteSerializer, DemoRequestSerializer,
    AccessReviewSerializer, UserGroupSerializer,
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


class MembershipViewSet(CsvExportMixin, viewsets.ModelViewSet):
    """Manage who belongs to the current tenant and what role they have.
    Scoped to the current tenant only — there is no cross-tenant listing."""

    serializer_class = MembershipSerializer
    permission_classes = [HasTenantRole]
    allowed_roles = ['admin']

    def get_queryset(self):
        tenant = _current_tenant()
        if tenant is None:
            return Membership.objects.none()
        qs = Membership.objects.filter(tenant=tenant).select_related('user')
        # The payoff of UserGroup (see its docstring): filter the roster
        # down to one team/department. `group__tenant=tenant` guards
        # against a group id from a different tenant matching nothing
        # here even in the edge case of one user belonging to two tenants.
        group_id = self.request.query_params.get('group')
        if group_id:
            qs = qs.filter(user__user_group_memberships__group_id=group_id, user__user_group_memberships__group__tenant=tenant)
        return qs

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

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """Record a completed access review for this Membership — ISO
        27001 A.5.18's "access rights shall be reviewed at regular
        intervals" made into actual evidence rather than a UI checkbox:
        an AccessReview row, permanent and immutable-by-construction (no
        endpoint ever updates or deletes one). A SUSPENDED outcome also
        deactivates the account immediately (DRF's TokenAuthentication
        checks User.is_active on every request, so this isn't just a
        flag that takes effect on next login)."""
        membership = self.get_object()
        outcome = request.data.get('outcome', AccessReview.Outcome.CONFIRMED)
        if outcome not in AccessReview.Outcome.values:
            return Response(
                {'outcome': [f'Must be one of: {", ".join(AccessReview.Outcome.values)}.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        review = AccessReview.objects.create(
            membership=membership, reviewed_by=request.user,
            outcome=outcome, notes=request.data.get('notes', ''),
        )
        log_action(
            request.user, AuditLog.Action.UPDATE, membership,
            metadata={'access_review': outcome, 'reviewed_username': membership.user.username},
        )

        if outcome == AccessReview.Outcome.SUSPENDED:
            membership.user.is_active = False
            membership.user.save(update_fields=['is_active'])

        return Response(MembershipSerializer(membership).data, status=status.HTTP_201_CREATED)


class AccessReviewViewSet(CsvExportMixin, viewsets.ReadOnlyModelViewSet):
    """Read-only history of every completed access review — the actual
    evidence trail for ISO 27001 A.5.18, exportable for an auditor.
    Visibility matches AuditLogViewSet's (admin/auditor only), since this
    is that same kind of control-evidence record."""

    serializer_class = AccessReviewSerializer
    permission_classes = [HasTenantRoleStrict]
    allowed_roles = ['admin', 'auditor']

    def get_queryset(self):
        tenant = _current_tenant()
        if tenant is None:
            return AccessReview.objects.none()
        return AccessReview.objects.filter(membership__tenant=tenant).select_related(
            'membership__user', 'reviewed_by',
        )


class UserGroupViewSet(CsvExportMixin, viewsets.ModelViewSet):
    """Named org-structure groups (department/team) — see UserGroup's
    docstring: not a permissions boundary, admin-only to manage, same
    tier as managing tenant members."""

    serializer_class = UserGroupSerializer
    permission_classes = [HasTenantRole]
    allowed_roles = ['admin']

    def get_queryset(self):
        tenant = _current_tenant()
        if tenant is None:
            return UserGroup.objects.none()
        return UserGroup.objects.filter(tenant=tenant).prefetch_related('members__user')

    def perform_create(self, serializer):
        tenant = _current_tenant()
        name = serializer.validated_data.get('name')
        # `tenant` isn't a serializer field (set here, not accepted from
        # the client), so DRF can't auto-generate a UniqueTogetherValidator
        # for UserGroup's (tenant, name) constraint — check by hand rather
        # than let a duplicate name surface as a raw IntegrityError.
        if UserGroup.objects.filter(tenant=tenant, name=name).exists():
            raise ValidationError({'name': ['A group with this name already exists.']})
        instance = serializer.save(tenant=tenant)
        log_action(self.request.user, AuditLog.Action.CREATE, instance)

    def perform_update(self, serializer):
        new_name = serializer.validated_data.get('name')
        if new_name and UserGroup.objects.filter(
            tenant=serializer.instance.tenant, name=new_name,
        ).exclude(pk=serializer.instance.pk).exists():
            raise ValidationError({'name': ['A group with this name already exists.']})
        instance = serializer.save()
        log_action(self.request.user, AuditLog.Action.UPDATE, instance)

    def perform_destroy(self, instance):
        log_action(self.request.user, AuditLog.Action.DELETE, instance)
        instance.delete()

    @action(detail=True, methods=['post'], url_path='add-member')
    def add_member(self, request, pk=None):
        group = self.get_object()
        username = request.data.get('username')
        user = User.objects.filter(username=username).first()
        if not user:
            return Response({'username': ['No such user.']}, status=status.HTTP_400_BAD_REQUEST)
        if not Membership.objects.filter(user=user, tenant=group.tenant).exists():
            return Response(
                {'username': ['This user is not a member of this tenant.']}, status=status.HTTP_400_BAD_REQUEST,
            )
        UserGroupMember.objects.get_or_create(group=group, user=user)
        log_action(request.user, AuditLog.Action.UPDATE, group, metadata={'added_username': user.username})
        # Re-fetch rather than reuse `group`: get_queryset() prefetches
        # `members`, and that cache is now stale — serializing the same
        # instance would report the pre-add member count/list.
        group = self.get_queryset().get(pk=group.pk)
        return Response(UserGroupSerializer(group).data)

    @action(detail=True, methods=['post'], url_path='remove-member')
    def remove_member(self, request, pk=None):
        group = self.get_object()
        user_id = request.data.get('user')
        UserGroupMember.objects.filter(group=group, user_id=user_id).delete()
        log_action(request.user, AuditLog.Action.UPDATE, group, metadata={'removed_user_id': user_id})
        # Same stale-prefetch-cache reasoning as add_member above.
        group = self.get_queryset().get(pk=group.pk)
        return Response(UserGroupSerializer(group).data)
