"""21 CFR Part 11 technical controls: electronic signatures (§11.50,
§11.70, §11.100, §11.200) and account-security safeguards (§11.300)."""

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db import connection
from django.test import TestCase
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
