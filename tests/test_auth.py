import json

from django.db import connection
from django.test import TestCase
from django.test import Client as DjangoTestClient
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from tenants.models import Client, Domain, Membership

# The old RBACPermissionTests class (testing accounts.permissions.IsInGroup)
# was removed along with that permission class: dead code from before
# Membership-based, per-tenant RBAC existed — see tenants/permissions.py's
# HasTenantRole for what actually gates access now.


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


class RemovedCrossTenantUserManagementTests(TestCase):
    """Regression test for a removed cross-tenant data leak: UserViewSet/
    GroupViewSet used to expose every user and Django Group platform-wide
    to any is_staff user, and every tenant's self-registered admin used to
    be is_staff. Both the endpoints and the privilege grant are gone now —
    this locks in that the endpoints stay gone even if someone adds them
    back to a router without thinking about the scoping again."""

    def test_users_and_groups_endpoints_no_longer_exist(self):
        connection.set_schema_to_public()
        tenant = Client.objects.create(schema_name='noleaktest', name='noleaktest')
        Domain.objects.create(domain='noleaktest.localhost', tenant=tenant, is_primary=True)

        User = get_user_model()
        admin_user = User.objects.create_user('noleak_admin', 'nla@example.com', 'pass12345')
        Membership.objects.create(user=admin_user, tenant=tenant, role=Membership.Role.ADMIN)

        api = APIClient()
        api.force_authenticate(user=admin_user)
        host = f'{tenant.schema_name}.localhost'

        self.assertEqual(api.get('/api/accounts/users/', HTTP_HOST=host).status_code, 404)
        self.assertEqual(api.get('/api/accounts/groups/', HTTP_HOST=host).status_code, 404)
