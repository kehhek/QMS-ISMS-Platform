from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.test import TestCase
from django_tenants.utils import schema_context
from rest_framework.test import APIClient

from tenants.models import Client, Domain, Membership

User = get_user_model()

# TenantMainMiddleware resolves a tenant from the Host header before any
# view runs — onboard_tenant forces the connection to public itself, but
# the request still needs *some* resolvable Host to reach the view at
# all. See test_registration.py for the same pattern.
PLATFORM_HOST = 'platform.localhost'


def make_tenant(schema_name):
    connection.set_schema_to_public()
    client = Client.objects.create(schema_name=schema_name, name=schema_name)
    Domain.objects.create(domain=f'{schema_name}.localhost', tenant=client, is_primary=True)
    return client


def make_platform_entrypoint():
    connection.set_schema_to_public()
    public_tenant, _ = Client.objects.get_or_create(schema_name='public', defaults={'name': 'Platform'})
    Domain.objects.get_or_create(domain=PLATFORM_HOST, defaults={'tenant': public_tenant, 'is_primary': True})


class TenantOnboardApiTests(TestCase):
    def test_onboarding_seeds_the_full_control_catalog(self):
        # Regression check: a platform-admin-provisioned tenant must start
        # with the full ISO 27001 + SOC 2 control catalog already loaded,
        # same as a self-service registration — traced back to a bug
        # report of controls being entirely missing after signup.
        make_platform_entrypoint()
        superuser = User.objects.create_superuser('platform_admin', 'pa@example.com', 'pass12345')

        api = APIClient()
        api.force_authenticate(user=superuser)
        resp = api.post('/api/accounts/onboard/', {
            'schema': 'org_onboardseedtest', 'name': 'Onboard Seed Test',
            'domain': 'onboardseedtest.localhost',
            'admin_username': 'onboard_admin', 'admin_email': 'oa@example.com',
        }, format='json', HTTP_HOST=PLATFORM_HOST)
        self.assertEqual(resp.status_code, 201, resp.data)

        with schema_context('org_onboardseedtest'):
            from core.models import Control
            self.assertEqual(Control.objects.count(), 126)

    def test_onboarding_does_not_grant_the_new_tenant_admin_global_staff_or_superuser(self):
        # Regression check: accounts.User is a SHARED_APP model — granting
        # is_staff/is_superuser to a per-tenant admin used to make them a
        # platform-wide Django superuser, able to read/edit every OTHER
        # tenant's data via /admin/. Membership.role=ADMIN is the correct,
        # tenant-scoped grant.
        make_platform_entrypoint()
        superuser = User.objects.create_superuser('platform_admin2', 'pa2@example.com', 'pass12345')

        api = APIClient()
        api.force_authenticate(user=superuser)
        resp = api.post('/api/accounts/onboard/', {
            'schema': 'org_onboardnoglobal', 'name': 'Onboard No Global Test',
            'domain': 'onboardnoglobal.localhost',
            'admin_username': 'no_global_admin', 'admin_email': 'nga@example.com',
        }, format='json', HTTP_HOST=PLATFORM_HOST)
        self.assertEqual(resp.status_code, 201, resp.data)

        with schema_context('org_onboardnoglobal'):
            new_admin = User.objects.get(username='no_global_admin')
            self.assertFalse(new_admin.is_staff)
            self.assertFalse(new_admin.is_superuser)

    def test_a_tenant_admin_cannot_provision_a_new_tenant(self):
        # Regression check: onboard_tenant used to be gated only by
        # IsAdminUser (is_staff), which every tenant's own admin used to
        # have — meaning any tenant admin could provision brand-new
        # tenants on the platform. Now requires true is_superuser.
        make_platform_entrypoint()
        tenant_only_admin = User.objects.create_user(
            'tenant_scoped_admin', 'tsa@example.com', 'pass12345', is_staff=True,
        )

        api = APIClient()
        api.force_authenticate(user=tenant_only_admin)
        resp = api.post('/api/accounts/onboard/', {
            'schema': 'org_shouldnotexist', 'name': 'Should Not Exist',
            'domain': 'shouldnotexist.localhost',
        }, format='json', HTTP_HOST=PLATFORM_HOST)
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(Client.objects.filter(schema_name='org_shouldnotexist').exists())


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
        # A password they didn't choose themselves — must be changed
        # before it can actually be used to log in (see test_part11.py's
        # MustChangePasswordTests for the login-side enforcement).
        self.assertTrue(User.objects.get(username='brand_new_auditor').must_change_password)

        # An email address was given, so an invite email should have gone
        # out with the generated credentials (best-effort — Django's test
        # runner swaps EMAIL_BACKEND to locmem automatically).
        self.assertTrue(resp.data['invite_email_sent'])
        from django.core import mail
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['bna@example.com'])
        self.assertIn(resp.data['generated_password'], mail.outbox[0].body)

    def test_inviting_without_an_email_does_not_attempt_to_send_one(self):
        tenant = make_tenant('onboardtestinvitenoemail')
        admin_user = User.objects.create_user('invite_admin2', 'ia2@example.com', 'pass12345')
        Membership.objects.create(user=admin_user, tenant=tenant, role=Membership.Role.ADMIN)

        api = APIClient()
        api.force_authenticate(user=admin_user)
        resp = api.post(
            '/api/tenant/members/',
            {'username': 'no_email_user', 'role': 'user'},
            HTTP_HOST=f'{tenant.schema_name}.localhost',
        )
        self.assertEqual(resp.status_code, 201)
        self.assertFalse(resp.data['invite_email_sent'])
        from django.core import mail
        self.assertEqual(len(mail.outbox), 0)

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


class MembershipResetPasswordTests(TestCase):
    def setUp(self):
        self.tenant = make_tenant('resetpwtest')
        self.host = f'{self.tenant.schema_name}.localhost'
        self.admin = User.objects.create_user('reset_admin', 'ra@example.com', 'pass12345')
        Membership.objects.create(user=self.admin, tenant=self.tenant, role=Membership.Role.ADMIN)
        self.target_user = User.objects.create_user('reset_target', 'rt@example.com', 'OriginalPass123')
        self.target_user.must_change_password = False
        self.target_user.save()
        self.membership = Membership.objects.create(user=self.target_user, tenant=self.tenant, role=Membership.Role.USER)

        self.api = APIClient()
        self.api.force_authenticate(user=self.admin)

    def test_non_admin_cannot_reset_someone_elses_password(self):
        api = APIClient()
        api.force_authenticate(user=self.target_user)
        resp = api.post(f'/api/tenant/members/{self.membership.pk}/reset-password/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 403)

    def test_admin_reset_invalidates_the_old_password_and_requires_a_change(self):
        resp = self.api.post(f'/api/tenant/members/{self.membership.pk}/reset-password/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertIn('generated_password', resp.data)

        self.target_user.refresh_from_db()
        self.assertFalse(self.target_user.check_password('OriginalPass123'))
        self.assertTrue(self.target_user.check_password(resp.data['generated_password']))
        self.assertTrue(self.target_user.must_change_password)

        # The new (admin-issued) password works, but login is blocked
        # pending a change — not just handed a token outright.
        login_resp = self.api.post(
            '/api/accounts/token/',
            {'username': 'reset_target', 'password': resp.data['generated_password']},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(login_resp.status_code, 403)
        self.assertTrue(login_resp.data['must_change_password'])

    def test_reset_clears_an_existing_lockout(self):
        self.target_user.failed_login_count = 5
        from django.utils import timezone
        import datetime
        self.target_user.locked_until = timezone.now() + datetime.timedelta(minutes=15)
        self.target_user.save()

        self.api.post(f'/api/tenant/members/{self.membership.pk}/reset-password/', HTTP_HOST=self.host)

        self.target_user.refresh_from_db()
        self.assertEqual(self.target_user.failed_login_count, 0)
        self.assertIsNone(self.target_user.locked_until)
