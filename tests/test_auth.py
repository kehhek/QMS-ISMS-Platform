import json

from django.db import connection
from django.test import TestCase
from django.test import Client as DjangoTestClient
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from types import SimpleNamespace
from accounts.permissions import IsInGroup
from tenants.models import Client, Domain


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


class TokenObtainCsrfTests(TestCase):
    """Regression test: a leftover Django admin session cookie in the same
    browser (admin and the frontend share the plain hostname `localhost` —
    cookies aren't port-scoped) used to make DRF's SessionAuthentication
    kick in on this exact endpoint's request, which has no Authorization
    header yet since obtaining one is the whole point, and its CSRF check
    then rejected a plain JSON POST with "CSRF Failed: CSRF token
    missing." Fixed via authentication_classes = [] on the view — this
    test only proves anything because enforce_csrf_checks=True, since
    Django's test client disables CSRF checking by default."""

    def test_token_obtain_works_despite_an_existing_admin_session(self):
        connection.set_schema_to_public()
        tenant = Client.objects.create(schema_name='csrftest', name='csrftest')
        Domain.objects.create(domain='csrftest.localhost', tenant=tenant, is_primary=True)

        User = get_user_model()
        User.objects.create_user(
            'session_user', 's@example.com', 'pass12345', is_staff=True, is_superuser=True,
        )

        client = DjangoTestClient(enforce_csrf_checks=True)
        host = f'{tenant.schema_name}.localhost'

        login_page = client.get('/admin/login/', HTTP_HOST=host)
        csrf_token = login_page.cookies['csrftoken'].value
        login_response = client.post(
            '/admin/login/',
            {'username': 'session_user', 'password': 'pass12345', 'csrfmiddlewaretoken': csrf_token},
            HTTP_HOST=host, HTTP_REFERER=f'http://{host}/admin/login/',
        )
        self.assertEqual(login_response.status_code, 302)  # confirms the session was really established

        token_response = client.post(
            '/api/accounts/token/',
            data=json.dumps({'username': 'session_user', 'password': 'pass12345'}),
            content_type='application/json',
            HTTP_HOST=host,
        )
        self.assertEqual(token_response.status_code, 200)
        self.assertIn('token', token_response.json())
