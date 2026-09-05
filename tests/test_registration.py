from django.core.cache import cache
from django.db import connection
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from tenants.models import Client, Domain, Membership
from django.contrib.auth import get_user_model

User = get_user_model()

# TenantMainMiddleware resolves a tenant from the Host header for every
# request *before* any view runs — including register(), even though the
# view itself doesn't care which tenant routed it here (it forces the
# connection to the public schema regardless). So the request still needs
# *some* resolvable Host, exactly like onboard_tenant. platform.localhost
# is the established convention for this class of platform-level
# operation (set up manually in dev; not part of any migration, so tests
# need to create it themselves).
PLATFORM_HOST = 'platform.localhost'


def make_platform_entrypoint():
    connection.set_schema_to_public()
    public_tenant, _ = Client.objects.get_or_create(schema_name='public', defaults={'name': 'Platform'})
    Domain.objects.get_or_create(domain=PLATFORM_HOST, defaults={'tenant': public_tenant, 'is_primary': True})


class RegistrationTests(TestCase):
    def setUp(self):
        make_platform_entrypoint()
        # The registration throttle (5/hour, by design — each call
        # provisions a real Postgres schema) lives in Django's cache, not
        # the DB, so it isn't reset by TestCase's transaction rollback.
        # Each test method otherwise inherits whatever quota prior methods
        # in this run consumed against the same 'registration' scope.
        cache.clear()

    def test_registration_creates_tenant_admin_and_returns_a_working_token(self):
        api = APIClient()
        response = api.post('/api/accounts/register/', {
            'org_name': 'Acme Corp',
            'subdomain': 'Acme Corp!!',
            'username': 'acme_founder',
            'email': 'founder@acme.example.com',
            'password': 'supersecret123',
            'plan': 'team',
        }, format='json', HTTP_HOST=PLATFORM_HOST)

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['schema'], 'org_acme_corp')
        self.assertEqual(response.data['domain'], 'acme-corp.localhost')
        self.assertTrue(response.data['token'])

        # The tenant, its admin user, and their membership really exist.
        tenant = Client.objects.get(schema_name='org_acme_corp')
        self.assertEqual(tenant.name, 'Acme Corp')
        self.assertEqual(tenant.plan, 'team')
        self.assertTrue(Domain.objects.filter(domain='acme-corp.localhost', tenant=tenant).exists())

        user = User.objects.get(username='acme_founder')
        membership = Membership.objects.get(user=user, tenant=tenant)
        self.assertEqual(membership.role, Membership.Role.ADMIN)

        # Regression check: accounts.User is a SHARED_APP model (global,
        # not per-tenant), so is_staff/is_superuser used to make every
        # self-registered tenant's founder a platform-wide Django
        # superuser — able to log into /admin/ and read/edit every OTHER
        # tenant's users, domains, and memberships. Membership.role=ADMIN
        # is the correct, tenant-scoped way to grant them admin access.
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

        # The returned token actually authenticates against the new tenant.
        dashboard = api.get(
            '/api/dashboard-summary/', HTTP_HOST='acme-corp.localhost',
            HTTP_AUTHORIZATION=f'Token {response.data["token"]}',
        )
        self.assertEqual(dashboard.status_code, 200)

        # Regression check: every newly registered tenant must start with
        # the full ISO 27001 + SOC 2 control catalog already loaded — a
        # bug report ("all the controls are missing from the control
        # page") traced back to tenants never having this seeded at all.
        controls = api.get(
            '/api/controls/?page_size=200', HTTP_HOST='acme-corp.localhost',
            HTTP_AUTHORIZATION=f'Token {response.data["token"]}',
        )
        self.assertEqual(controls.status_code, 200)
        self.assertEqual(controls.data['count'], 126)

    def test_duplicate_subdomain_is_rejected(self):
        api = APIClient()
        payload = {
            'org_name': 'Dup Co', 'subdomain': 'dupco', 'username': 'dup_user1',
            'email': 'a@dupco.example.com', 'password': 'supersecret123',
        }
        first = api.post('/api/accounts/register/', payload, format='json', HTTP_HOST=PLATFORM_HOST)
        self.assertEqual(first.status_code, 201)

        payload2 = dict(payload, username='dup_user2', email='b@dupco.example.com')
        second = api.post('/api/accounts/register/', payload2, format='json', HTTP_HOST=PLATFORM_HOST)
        self.assertEqual(second.status_code, 400)
        self.assertIn('subdomain', second.data)

    def test_duplicate_username_is_rejected(self):
        api = APIClient()
        api.post('/api/accounts/register/', {
            'org_name': 'First Co', 'subdomain': 'firstco', 'username': 'shared_name',
            'email': 'a@firstco.example.com', 'password': 'supersecret123',
        }, format='json', HTTP_HOST=PLATFORM_HOST)

        response = api.post('/api/accounts/register/', {
            'org_name': 'Second Co', 'subdomain': 'secondco', 'username': 'shared_name',
            'email': 'b@secondco.example.com', 'password': 'supersecret123',
        }, format='json', HTTP_HOST=PLATFORM_HOST)
        self.assertEqual(response.status_code, 400)
        self.assertIn('username', response.data)

    @override_settings(DEBUG=False)
    def test_dev_domain_repointing_is_skipped_outside_debug(self):
        api = APIClient()
        api.post('/api/accounts/register/', {
            'org_name': 'Prod Co', 'subdomain': 'prodco', 'username': 'prod_user',
            'email': 'a@prodco.example.com', 'password': 'supersecret123',
        }, format='json', HTTP_HOST=PLATFORM_HOST)
        self.assertFalse(Domain.objects.filter(domain='localhost', tenant__schema_name='org_prodco').exists())
