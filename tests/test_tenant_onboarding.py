from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.test import TestCase
from rest_framework.test import APIClient

from tenants.models import Client, Domain, Membership

User = get_user_model()


def make_tenant(schema_name):
    connection.set_schema_to_public()
    client = Client.objects.create(schema_name=schema_name, name=schema_name)
    Domain.objects.create(domain=f'{schema_name}.localhost', tenant=client, is_primary=True)
    return client


class MembershipModelTests(TestCase):
    def test_a_user_can_only_have_one_membership_per_tenant(self):
        tenant = make_tenant('onboardtestuniq')
        user = User.objects.create_user('dup_user', 'dup@example.com', 'pass12345')
        Membership.objects.create(user=user, tenant=tenant, role=Membership.Role.USER)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Membership.objects.create(user=user, tenant=tenant, role=Membership.Role.ADMIN)


class TenantSettingsApiTests(TestCase):
    def test_admin_member_can_view_and_update_settings(self):
        tenant = make_tenant('onboardtestsettingsadmin')
        admin_user = User.objects.create_user('settings_admin', 'sa@example.com', 'pass12345')
        Membership.objects.create(user=admin_user, tenant=tenant, role=Membership.Role.ADMIN)

        api = APIClient()
        api.force_authenticate(user=admin_user)

        get_resp = api.get('/api/tenant/settings/', HTTP_HOST=f'{tenant.schema_name}.localhost')
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(get_resp.data['schema_name'], tenant.schema_name)

        patch_resp = api.patch(
            '/api/tenant/settings/', {'support_email': 'help@example.com'},
            HTTP_HOST=f'{tenant.schema_name}.localhost',
        )
        self.assertEqual(patch_resp.status_code, 200)
        self.assertEqual(patch_resp.data['support_email'], 'help@example.com')

    def test_non_admin_member_cannot_update_settings(self):
        tenant = make_tenant('onboardtestsettingsuser')
        plain_user = User.objects.create_user('settings_user', 'su@example.com', 'pass12345')
        Membership.objects.create(user=plain_user, tenant=tenant, role=Membership.Role.USER)

        api = APIClient()
        api.force_authenticate(user=plain_user)

        patch_resp = api.patch(
            '/api/tenant/settings/', {'support_email': 'nope@example.com'},
            HTTP_HOST=f'{tenant.schema_name}.localhost',
        )
        self.assertEqual(patch_resp.status_code, 403)


class MembershipApiTests(TestCase):
    def test_admin_can_invite_a_new_user_with_a_role(self):
        tenant = make_tenant('onboardtestinvite')
        admin_user = User.objects.create_user('invite_admin', 'ia@example.com', 'pass12345')
        Membership.objects.create(user=admin_user, tenant=tenant, role=Membership.Role.ADMIN)

        api = APIClient()
        api.force_authenticate(user=admin_user)
        resp = api.post(
            '/api/tenant/members/',
            {'username': 'brand_new_auditor', 'email': 'bna@example.com', 'role': 'auditor'},
            HTTP_HOST=f'{tenant.schema_name}.localhost',
        )
        self.assertEqual(resp.status_code, 201)
        self.assertIn('generated_password', resp.data)
        self.assertTrue(User.objects.filter(username='brand_new_auditor').exists())
        self.assertTrue(
            Membership.objects.filter(
                user__username='brand_new_auditor', tenant=tenant, role='auditor',
            ).exists()
        )

    def test_non_admin_cannot_invite_members(self):
        tenant = make_tenant('onboardtestinvitedeny')
        plain_user = User.objects.create_user('invite_user', 'iu@example.com', 'pass12345')
        Membership.objects.create(user=plain_user, tenant=tenant, role=Membership.Role.USER)

        api = APIClient()
        api.force_authenticate(user=plain_user)
        resp = api.post(
            '/api/tenant/members/',
            {'username': 'should_not_exist', 'role': 'user'},
            HTTP_HOST=f'{tenant.schema_name}.localhost',
        )
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(User.objects.filter(username='should_not_exist').exists())
