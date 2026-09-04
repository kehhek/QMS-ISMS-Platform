from rest_framework import permissions


class IsInGroupOrReadOnly(permissions.BasePermission):
    """Any authenticated user can read (list/retrieve). Write access
    (create/update/delete) requires membership in one of the view's
    `allowed_groups`, or superuser status. If a view doesn't set
    `allowed_groups`, write access is open to any authenticated user.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        if user.is_superuser:
            return True
        allowed = getattr(view, 'allowed_groups', None)
        if not allowed:
            return True
        return user.groups.filter(name__in=allowed).exists()
