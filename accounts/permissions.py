from rest_framework import permissions


class IsInGroup(permissions.BasePermission):
    """Allow access only to users in one of the allowed groups.

    Views can set an `allowed_groups` attribute (list/tuple of group names).
    If not set, access is allowed (useful for public endpoints).
    """

    def has_permission(self, request, view):
        allowed = getattr(view, 'allowed_groups', None)
        if not allowed:
            return True
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return user.groups.filter(name__in=allowed).exists()
