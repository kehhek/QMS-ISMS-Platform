from django.db import connection

from rest_framework import permissions

from .models import Membership


def get_role(user, tenant=None):
    """The user's Membership.role for `tenant` (default: whichever tenant
    is active on the connection for this request), or None if they have
    no membership there. Superuser status is a separate, global check —
    callers should check `user.is_superuser` themselves if it should
    bypass role checks."""
    if not getattr(user, 'is_authenticated', False):
        return None
    if tenant is None:
        tenant = getattr(connection, 'tenant', None)
    if tenant is None:
        return None
    membership = Membership.objects.filter(user=user, tenant=tenant).first()
    return membership.role if membership else None


class HasTenantRole(permissions.BasePermission):
    """Tenant-scoped RBAC: a user's role is looked up via Membership for
    whichever tenant the current request is being served for, not via
    global Django Groups (auth.Group is shared across every tenant, which
    would make "Auditor" a platform-wide role instead of a per-org one).

    Any authenticated user with *some* membership in the current tenant
    can read (list/retrieve). Write access requires a role in the view's
    `allowed_roles`, or superuser status. A view with no `allowed_roles`
    set allows writes to any member of the tenant.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True

        role = get_role(user)
        if request.method in permissions.SAFE_METHODS:
            return role is not None

        allowed = getattr(view, 'allowed_roles', None)
        if not allowed:
            return role is not None
        return role in allowed
