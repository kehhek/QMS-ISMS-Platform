from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from types import SimpleNamespace
from accounts.permissions import IsInGroup


class RBACPermissionTests(TestCase):
    def test_is_in_group_permission_allows_when_user_in_group(self):
        User = get_user_model()
        user = User.objects.create_user('u1', 'u1@example.com', 'pass')
        grp = Group.objects.create(name='admin')
        user.groups.add(grp)

        perm = IsInGroup()
        fake_view = SimpleNamespace(allowed_groups=['admin'])
        fake_request = SimpleNamespace(user=user)

        self.assertTrue(perm.has_permission(fake_request, fake_view))

    def test_is_in_group_permission_denies_when_not_in_group(self):
        User = get_user_model()
        user = User.objects.create_user('u2', 'u2@example.com', 'pass')
        perm = IsInGroup()
        fake_view = SimpleNamespace(allowed_groups=['admin'])
        fake_request = SimpleNamespace(user=user)

        self.assertFalse(perm.has_permission(fake_request, fake_view))
