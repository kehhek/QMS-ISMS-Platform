"""21 CFR Part 11 technical controls: electronic signatures (§11.50,
§11.70, §11.100, §11.200) and account-security safeguards (§11.300)."""

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db import connection
from django.test import Client as DjangoTestClient, TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from tenants.models import Client, Domain, Membership

User = get_user_model()


def make_tenant(schema_name):
    connection.set_schema_to_public()
    client = Client.objects.create(schema_name=schema_name, name=schema_name)
    Domain.objects.create(domain=f'{schema_name}.localhost', tenant=client, is_primary=True)
    return client


def make_member(tenant, username, role, password='pass12345'):
    user = User.objects.create_user(username, f'{username}@example.com', password)
    Membership.objects.create(user=user, tenant=tenant, role=role)
    return user


class ElectronicSignatureTests(TestCase):
    def setUp(self):
        self.tenant = make_tenant('sigtest')
        self.host = f'{self.tenant.schema_name}.localhost'
        self.admin = make_member(self.tenant, 'sig_admin', Membership.Role.ADMIN, password='RealPassword123')

        from django_tenants.utils import schema_context
        with schema_context(self.tenant.schema_name):
            from core.models import Document
            self.document = Document.objects.create(title='Sig Test Doc', content='v1')

        self.api = APIClient()
        self.api.force_authenticate(user=self.admin)
        workflow = self.api.post(
            '/api/workflows/',
            {'document': self.document.pk, 'new_steps': [{'order': 1, 'approver_role': 'admin'}]},
            format='json', HTTP_HOST=self.host,
        )
        self.step_id = workflow.data['steps'][0]['id']

    def test_decide_without_password_is_rejected_and_creates_no_signature(self):
        resp = self.api.post(f'/api/workflow-steps/{self.step_id}/decide/', {'decision': 'approved'}, HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 403)

        from django_tenants.utils import schema_context
        with schema_context(self.tenant.schema_name):
            from core.models import ElectronicSignature, WorkflowStep
            self.assertEqual(ElectronicSignature.objects.count(), 0)
            self.assertEqual(WorkflowStep.objects.get(pk=self.step_id).status, WorkflowStep.Status.PENDING)

    def test_decide_with_wrong_password_is_rejected(self):
        resp = self.api.post(
            f'/api/workflow-steps/{self.step_id}/decide/',
            {'decision': 'approved', 'password': 'totally-wrong'}, HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 403)

        from django_tenants.utils import schema_context
        with schema_context(self.tenant.schema_name):
            from core.models import AuditLog
            self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.SIGNATURE_FAILED).exists())

    def test_decide_with_correct_password_creates_a_valid_linked_signature(self):
        resp = self.api.post(
            f'/api/workflow-steps/{self.step_id}/decide/',
            {'decision': 'approved', 'password': 'RealPassword123'}, HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 200, resp.data)

        from django_tenants.utils import schema_context
        with schema_context(self.tenant.schema_name):
            from core.models import ElectronicSignature, WorkflowStep
            step = WorkflowStep.objects.get(pk=self.step_id)
            signature = ElectronicSignature.objects.get(
                content_type=ContentType.objects.get_for_model(step), object_id=step.pk,
            )
            self.assertEqual(signature.meaning, ElectronicSignature.Meaning.APPROVED)
            self.assertEqual(signature.printed_name, 'sig_admin')  # no first/last name set — falls back to username
            self.assertTrue(signature.verify())

    def test_signature_is_immutable(self):
        from django_tenants.utils import schema_context
        with schema_context(self.tenant.schema_name):
            from core.models import Document, ElectronicSignature

            signature = ElectronicSignature(
                user=self.admin, printed_name='Someone', meaning=ElectronicSignature.Meaning.APPROVED,
                content_type=ContentType.objects.get_for_model(self.document), object_id=self.document.pk,
                target_repr='x',
            )
            signature.save()
            original_hash = signature.integrity_hash

            signature.meaning = ElectronicSignature.Meaning.REJECTED
            with self.assertRaises(ValueError):
                signature.save()

            with self.assertRaises(ValueError):
                signature.delete()

            # Tampering via a bypass of the ORM guard is still caught — by
            # the DB trigger for the write itself, and by verify() for any
            # hash mismatch that somehow got through. The DB error has to
            # be isolated in its own savepoint: left inside the outer
            # TestCase transaction, Postgres marks the whole transaction
            # aborted and every later query here would fail too, even
            # though the Python exception itself was caught.
            from django.db import transaction
            with self.assertRaises(Exception):
                with transaction.atomic():
                    ElectronicSignature.objects.filter(pk=signature.pk).update(meaning='rejected')

            signature.refresh_from_db()
            self.assertEqual(signature.integrity_hash, original_hash)
            self.assertTrue(signature.verify())

    def test_tampering_with_a_signed_field_is_detected_by_verify(self):
        from django_tenants.utils import schema_context
        with schema_context(self.tenant.schema_name):
            from core.models import ElectronicSignature

            signature = ElectronicSignature(
                user=self.admin, printed_name='Someone', meaning=ElectronicSignature.Meaning.APPROVED,
                content_type=ContentType.objects.get_for_model(self.document), object_id=self.document.pk,
                target_repr='x',
            )
            signature.save()
            self.assertTrue(signature.verify())

            # Simulate a row that was altered by some means the trigger
            # doesn't cover (e.g. a direct DB restore) — verify() must
            # still catch the mismatch rather than trusting the stored hash.
            signature.printed_name = 'A Different Person'
            self.assertFalse(signature.verify())


class AccountLockoutTests(TestCase):
    def setUp(self):
        self.tenant = make_tenant('lockouttest')
        self.host = f'{self.tenant.schema_name}.localhost'
        self.user = make_member(self.tenant, 'lockout_user', Membership.Role.USER, password='RealPassword123')

    def _attempt_login(self, password):
        api = APIClient()
        return api.post(
            '/api/accounts/token/', {'username': 'lockout_user', 'password': password},
            format='json', HTTP_HOST=self.host,
        )

    def test_account_locks_after_max_failed_attempts_and_blocks_even_the_correct_password(self):
        from django.conf import settings
        for _ in range(settings.PART11_MAX_FAILED_LOGINS):
            resp = self._attempt_login('wrong-password')
            self.assertEqual(resp.status_code, 400)

        locked_resp = self._attempt_login('RealPassword123')
        self.assertEqual(locked_resp.status_code, 403)
        self.assertIn('locked', locked_resp.data['detail'].lower())

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_locked())

    def test_successful_login_resets_the_failed_count(self):
        self._attempt_login('wrong-password')
        self._attempt_login('wrong-password')
        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_login_count, 2)

        ok = self._attempt_login('RealPassword123')
        self.assertEqual(ok.status_code, 200)

        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_login_count, 0)
        self.assertIsNone(self.user.locked_until)


class AdminLoginLockoutTests(TestCase):
    """Part11LockoutBackend (accounts/backends.py) is what makes this
    pass — Django admin's own /admin/login/ used to authenticate via the
    plain default ModelBackend, which has no idea failed_login_count/
    locked_until exist, so repeated wrong passwords there never
    triggered a lockout at all. This is the same protection
    AccountLockoutTests already covers for the API login endpoints,
    exercised through /admin/login/ instead — a different Django view
    entirely, but the same authenticate() call underneath now that the
    backend itself is where lockout enforcement lives."""

    def setUp(self):
        from django.conf import settings
        self.settings = settings
        self.tenant = make_tenant('adminlockouttest')
        self.host = f'{self.tenant.schema_name}.localhost'
        self.admin = make_member(self.tenant, 'adminlock_admin', Membership.Role.ADMIN, password='RealPassword123')

    def _attempt_admin_login(self, password, client=None):
        client = client or DjangoTestClient()
        return client.post(
            '/admin/login/', {'username': 'adminlock_admin', 'password': password},
            HTTP_HOST=self.host,
        )

    def test_admin_login_locks_after_max_failed_attempts(self):
        for _ in range(self.settings.PART11_MAX_FAILED_LOGINS):
            self._attempt_admin_login('wrong-password')

        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_locked())

        # Even the correct password is refused once locked.
        resp = self._attempt_admin_login('RealPassword123')
        # A failed admin login re-renders the login form (200) rather
        # than redirecting (302, which only a successful login does).
        self.assertEqual(resp.status_code, 200)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_locked())

    def test_admin_login_does_not_double_count_failures(self):
        self._attempt_admin_login('wrong-password')
        self._attempt_admin_login('wrong-password')
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.failed_login_count, 2)

    def test_a_lockout_started_via_the_api_also_blocks_admin_login(self):
        """The lockout is a property of the account, not of whichever
        view happened to trigger it — enforced in one shared backend
        now, not duplicated per view."""
        api = APIClient()
        for _ in range(self.settings.PART11_MAX_FAILED_LOGINS):
            api.post(
                '/api/accounts/token/', {'username': 'adminlock_admin', 'password': 'wrong-password'},
                format='json', HTTP_HOST=self.host,
            )
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_locked())

        client = DjangoTestClient()
        resp = self._attempt_admin_login('RealPassword123', client=client)
        self.assertEqual(resp.status_code, 200)  # refused, form re-rendered
        self.assertNotIn('_auth_user_id', client.session)


class PasswordPolicyTests(TestCase):
    # TenantMainMiddleware resolves a tenant from the Host header before
    # any view runs — register() needs *some* resolvable domain to be
    # reached at all, same as onboard_tenant. See test_registration.py.
    PLATFORM_HOST = 'platform.localhost'

    def setUp(self):
        connection.set_schema_to_public()
        public_tenant, _ = Client.objects.get_or_create(schema_name='public', defaults={'name': 'Platform'})
        Domain.objects.get_or_create(domain=self.PLATFORM_HOST, defaults={'tenant': public_tenant, 'is_primary': True})
        # See test_registration.py — the registration throttle lives in
        # Django's cache, not the DB, so it survives TestCase's rollback
        # and isn't reset between test methods on its own.
        cache.clear()

    def test_weak_password_rejected_at_registration(self):
        api = APIClient()
        resp = api.post('/api/accounts/register/', {
            'org_name': 'Weak Co', 'subdomain': 'weakco9', 'username': 'weak_user9',
            'email': 'a@weakco9.example.com', 'password': '12345',
        }, format='json', HTTP_HOST=self.PLATFORM_HOST)
        self.assertEqual(resp.status_code, 400)
        self.assertIn('password', resp.data)

    def test_strong_password_accepted_at_registration(self):
        api = APIClient()
        resp = api.post('/api/accounts/register/', {
            'org_name': 'Strong Co', 'subdomain': 'strongco9', 'username': 'strong_user9',
            'email': 'a@strongco9.example.com', 'password': 'Xk9$mQp2wZ!7',
        }, format='json', HTTP_HOST=self.PLATFORM_HOST)
        self.assertEqual(resp.status_code, 201, resp.data)


class PasswordAgeTests(TestCase):
    def test_set_password_stamps_password_changed_at(self):
        tenant = make_tenant('pwage')
        user = make_member(tenant, 'pw_user', Membership.Role.USER)
        old_stamp = user.password_changed_at

        user.set_password('ANewPassword123')
        user.save()
        self.assertGreater(user.password_changed_at, old_stamp)

    def test_password_expired_reports_correctly(self):
        tenant = make_tenant('pwage2')
        user = make_member(tenant, 'pw_user2', Membership.Role.USER)

        self.assertFalse(user.password_expired(90))

        user.password_changed_at = timezone.now() - timezone.timedelta(days=100)
        self.assertTrue(user.password_expired(90))


class PasswordExpiryEnforcementTests(TestCase):
    """Part 11 §11.300(b): periodic password revision — expired() being
    merely *tracked* isn't enough; login must actually block on it, and
    there must be a way to get unblocked without an admin's help."""

    def setUp(self):
        # AnonRateThrottle's state lives in Django's cache, not the DB —
        # survives TestCase's rollback and accumulates across every other
        # test in the run that hits an anon-throttled endpoint. See the
        # identical note in test_registration.py.
        cache.clear()
        self.tenant = make_tenant('pwexpiry')
        self.host = f'{self.tenant.schema_name}.localhost'
        self.user = make_member(self.tenant, 'expiry_user', Membership.Role.USER, password='OldPassword123')
        self.user.password_changed_at = timezone.now() - timezone.timedelta(days=100)
        self.user.save()

    def test_token_login_is_blocked_for_an_expired_password(self):
        api = APIClient()
        resp = api.post(
            '/api/accounts/token/', {'username': 'expiry_user', 'password': 'OldPassword123'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(resp.data['password_expired'])

    def test_session_login_is_blocked_for_an_expired_password(self):
        api = APIClient()
        resp = api.post(
            '/api/accounts/login/', {'username': 'expiry_user', 'password': 'OldPassword123'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(resp.data['password_expired'])

    def test_wrong_old_password_is_rejected_by_the_expired_change_flow(self):
        api = APIClient()
        resp = api.post(
            '/api/accounts/password/change-expired/',
            {'username': 'expiry_user', 'old_password': 'totally-wrong', 'new_password': 'BrandNewPass123'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 400)

    def test_weak_new_password_is_rejected_by_the_expired_change_flow(self):
        api = APIClient()
        resp = api.post(
            '/api/accounts/password/change-expired/',
            {'username': 'expiry_user', 'old_password': 'OldPassword123', 'new_password': '12345'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('new_password', resp.data)

    def test_changing_an_expired_password_issues_a_working_token(self):
        api = APIClient()
        resp = api.post(
            '/api/accounts/password/change-expired/',
            {'username': 'expiry_user', 'old_password': 'OldPassword123', 'new_password': 'BrandNewPass123'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        token = resp.data['token']

        self.user.refresh_from_db()
        self.assertFalse(self.user.password_expired(90))

        # The new token actually works now.
        dashboard = api.get(
            '/api/dashboard-summary/', HTTP_HOST=self.host, HTTP_AUTHORIZATION=f'Token {token}',
        )
        self.assertEqual(dashboard.status_code, 200)

        # And the old password no longer does.
        old_login = api.post(
            '/api/accounts/token/', {'username': 'expiry_user', 'password': 'OldPassword123'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(old_login.status_code, 400)


class MustChangePasswordTests(TestCase):
    """A password an admin handed someone (invite or reset) rather than
    one they chose themselves — must be replaced before it can actually
    log in, same enforcement shape as password_expired but a distinct
    reason (see accounts/models.py User.must_change_password)."""

    def setUp(self):
        cache.clear()
        self.tenant = make_tenant('mustchangepw')
        self.host = f'{self.tenant.schema_name}.localhost'
        self.user = make_member(self.tenant, 'mustchange_user', Membership.Role.USER, password='TempPass123')
        self.user.must_change_password = True
        self.user.save()

    def test_token_login_is_blocked_until_the_password_is_changed(self):
        api = APIClient()
        resp = api.post(
            '/api/accounts/token/', {'username': 'mustchange_user', 'password': 'TempPass123'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(resp.data['must_change_password'])
        self.assertNotIn('password_expired', resp.data)

    def test_session_login_is_also_blocked(self):
        api = APIClient()
        resp = api.post(
            '/api/accounts/login/', {'username': 'mustchange_user', 'password': 'TempPass123'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(resp.data['must_change_password'])

    def test_wrong_password_is_still_just_a_login_failure_not_a_leak(self):
        # A wrong password on a must-change account looks exactly like a
        # wrong password anywhere else — it doesn't first confirm the
        # account exists and needs a change before checking credentials.
        api = APIClient()
        resp = api.post(
            '/api/accounts/token/', {'username': 'mustchange_user', 'password': 'totally-wrong'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 400)

    def test_the_same_change_expired_endpoint_clears_the_flag_and_issues_a_token(self):
        api = APIClient()
        resp = api.post(
            '/api/accounts/password/change-expired/',
            {'username': 'mustchange_user', 'old_password': 'TempPass123', 'new_password': 'MyOwnChoice123'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertIn('token', resp.data)

        self.user.refresh_from_db()
        self.assertFalse(self.user.must_change_password)

        # Now logs in normally with the new password, no more block.
        login_resp = api.post(
            '/api/accounts/token/', {'username': 'mustchange_user', 'password': 'MyOwnChoice123'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(login_resp.status_code, 200)

    def test_a_voluntary_change_password_call_also_clears_the_flag(self):
        api = APIClient()
        api.force_authenticate(user=self.user)
        resp = api.post(
            '/api/accounts/password/change/',
            {'old_password': 'TempPass123', 'new_password': 'MyOwnChoice123'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.user.refresh_from_db()
        self.assertFalse(self.user.must_change_password)


class ChangePasswordViewTests(TestCase):
    def setUp(self):
        self.tenant = make_tenant('pwchange')
        self.host = f'{self.tenant.schema_name}.localhost'
        self.user = make_member(self.tenant, 'change_user', Membership.Role.USER, password='CurrentPass123')

    def test_authenticated_user_can_change_their_own_password(self):
        api = APIClient()
        api.force_authenticate(user=self.user)
        resp = api.post(
            '/api/accounts/password/change/',
            {'old_password': 'CurrentPass123', 'new_password': 'FreshPassword456'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 200, resp.data)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('FreshPassword456'))

    def test_wrong_old_password_is_rejected(self):
        api = APIClient()
        api.force_authenticate(user=self.user)
        resp = api.post(
            '/api/accounts/password/change/',
            {'old_password': 'nope', 'new_password': 'FreshPassword456'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 400)

    def test_requires_authentication(self):
        api = APIClient()
        resp = api.post(
            '/api/accounts/password/change/',
            {'old_password': 'CurrentPass123', 'new_password': 'FreshPassword456'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 401)


class ForgotPasswordFlowTests(TestCase):
    def setUp(self):
        cache.clear()
        self.tenant = make_tenant('forgotpw')
        self.host = f'{self.tenant.schema_name}.localhost'
        self.user = make_member(self.tenant, 'forgot_user', Membership.Role.USER, password='OriginalPass123')
        self.user.email = 'forgot_user@example.com'
        self.user.save()

    def _request_reset(self, username):
        api = APIClient()
        return api.post(
            '/api/accounts/password/reset/', {'username': username}, format='json', HTTP_HOST=self.host,
        )

    def test_request_always_returns_the_same_generic_response(self):
        real = self._request_reset('forgot_user')
        fake = self._request_reset('no_such_user_at_all')
        self.assertEqual(real.status_code, 200)
        self.assertEqual(fake.status_code, 200)
        self.assertEqual(real.data, fake.data)

    def test_a_real_request_sends_exactly_one_email_with_a_working_link(self):
        resp = self._request_reset('forgot_user')
        self.assertEqual(resp.status_code, 200)

        from django.core import mail
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['forgot_user@example.com'])
        self.assertIn('uid=', mail.outbox[0].body)
        self.assertIn('token=', mail.outbox[0].body)

    def test_a_fake_username_sends_no_email(self):
        self._request_reset('no_such_user_at_all')
        from django.core import mail
        self.assertEqual(len(mail.outbox), 0)

    def _extract_uid_and_token(self, email_body):
        import re
        uid = re.search(r'uid=([^&\s]+)', email_body).group(1)
        token = re.search(r'token=([^&\s]+)', email_body).group(1)
        return uid, token

    def test_confirming_with_the_emailed_link_sets_a_working_new_password(self):
        self._request_reset('forgot_user')
        from django.core import mail
        uid, token = self._extract_uid_and_token(mail.outbox[0].body)

        api = APIClient()
        resp = api.post(
            '/api/accounts/password/reset-confirm/',
            {'uid': uid, 'token': token, 'new_password': 'BrandNewPass789'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        new_token = resp.data['token']

        dashboard = api.get(
            '/api/dashboard-summary/', HTTP_HOST=self.host, HTTP_AUTHORIZATION=f'Token {new_token}',
        )
        self.assertEqual(dashboard.status_code, 200)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('BrandNewPass789'))

    def test_a_used_token_cannot_be_replayed(self):
        self._request_reset('forgot_user')
        from django.core import mail
        uid, token = self._extract_uid_and_token(mail.outbox[0].body)

        api = APIClient()
        first = api.post(
            '/api/accounts/password/reset-confirm/',
            {'uid': uid, 'token': token, 'new_password': 'FirstNewPass123'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(first.status_code, 200)

        replay = api.post(
            '/api/accounts/password/reset-confirm/',
            {'uid': uid, 'token': token, 'new_password': 'SecondNewPass456'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(replay.status_code, 400)

    def test_a_tampered_token_is_rejected(self):
        self._request_reset('forgot_user')
        from django.core import mail
        uid, _token = self._extract_uid_and_token(mail.outbox[0].body)

        api = APIClient()
        resp = api.post(
            '/api/accounts/password/reset-confirm/',
            {'uid': uid, 'token': 'not-a-real-token', 'new_password': 'BrandNewPass789'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 400)

    def test_weak_new_password_is_rejected_on_confirm(self):
        self._request_reset('forgot_user')
        from django.core import mail
        uid, token = self._extract_uid_and_token(mail.outbox[0].body)

        api = APIClient()
        resp = api.post(
            '/api/accounts/password/reset-confirm/',
            {'uid': uid, 'token': token, 'new_password': '12345'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('new_password', resp.data)
