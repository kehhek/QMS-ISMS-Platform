"""Continuous, automated control evidence via connected third-party
integrations (GitHub, AWS) — see core/integrations/. Provider HTTP calls
are mocked here (standard practice for third-party API integrations —
real network calls in a test suite are flaky and rate-limited); the
actual GitHub/AWS wire format was verified live, separately, against the
real APIs before shipping."""

from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django_tenants.utils import schema_context
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


class IntegrationPermissionTests(TestCase):
    def setUp(self):
        self.tenant = make_tenant('integrationperms')
        self.host = f'{self.tenant.schema_name}.localhost'
        self.admin = make_member(self.tenant, 'int_admin', Membership.Role.ADMIN)
        self.auditor = make_member(self.tenant, 'int_auditor', Membership.Role.AUDITOR)
        self.plain_user = make_member(self.tenant, 'int_user', Membership.Role.USER)

    def _create(self, actor):
        api = APIClient()
        api.force_authenticate(user=actor)
        return api, api.post(
            '/api/integrations/',
            {
                'provider': 'github', 'name': 'Acme GitHub',
                'config': {'owner': 'acme', 'repo': 'backend', 'branch': 'main'},
                'credentials': {'token': 'ghp_faketoken'},
            },
            format='json', HTTP_HOST=self.host,
        )

    def test_admin_can_create_an_integration(self):
        api, resp = self._create(self.admin)
        self.assertEqual(resp.status_code, 201, resp.data)

    def test_auditor_cannot_create_an_integration(self):
        api, resp = self._create(self.auditor)
        self.assertEqual(resp.status_code, 403)

    def test_plain_user_cannot_even_list_integrations(self):
        user_api = APIClient()
        user_api.force_authenticate(user=self.plain_user)
        resp = user_api.get('/api/integrations/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 403)

    def test_auditor_can_view_but_not_edit(self):
        api, created = self._create(self.admin)
        auditor_api = APIClient()
        auditor_api.force_authenticate(user=self.auditor)

        listing = auditor_api.get('/api/integrations/', HTTP_HOST=self.host)
        self.assertEqual(listing.status_code, 200)

        edit = auditor_api.patch(
            f'/api/integrations/{created.data["id"]}/', {'name': 'renamed'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(edit.status_code, 403)

    def test_credentials_are_never_returned_and_are_encrypted_at_rest(self):
        api, resp = self._create(self.admin)
        self.assertNotIn('credentials', resp.data)
        self.assertTrue(resp.data['has_credentials'])

        with schema_context(self.tenant.schema_name):
            from core.models import Integration
            integration = Integration.objects.get(pk=resp.data['id'])
            # The raw secret must not appear anywhere in the stored blob.
            self.assertNotIn('ghp_faketoken', integration.encrypted_credentials)
            self.assertEqual(integration.get_credentials(), {'token': 'ghp_faketoken'})


class GitHubSyncTests(TestCase):
    """Mocks GitHubProvider._get (the one place it talks to the network)
    to simulate real GitHub API responses, so the rest of the sync
    pipeline (Control update, Evidence creation, IntegrationCheckResult
    history) is tested without a live network call."""

    def setUp(self):
        self.tenant = make_tenant('githubsynctest')
        self.host = f'{self.tenant.schema_name}.localhost'
        self.admin = make_member(self.tenant, 'gh_admin', Membership.Role.ADMIN)
        with schema_context(self.tenant.schema_name):
            from core.models import Control
            Control.objects.create(framework='iso27001', identifier='A.8.32', name='Change management')
            Control.objects.create(framework='iso27001', identifier='A.8.25', name='Secure development life cycle')

        self.api = APIClient()
        self.api.force_authenticate(user=self.admin)
        create = self.api.post(
            '/api/integrations/',
            {
                'provider': 'github', 'name': 'Acme GitHub',
                'config': {'owner': 'acme', 'repo': 'backend', 'branch': 'main'},
                'credentials': {'token': 'ghp_faketoken'},
            },
            format='json', HTTP_HOST=self.host,
        )
        self.integration_id = create.data['id']

    @patch('core.integrations.github.GitHubProvider._get')
    def test_sync_marks_controls_implemented_when_checks_pass(self, mock_get):
        # First call: branch info (protected=True). Second: protection
        # rules (required_pull_request_reviews present).
        mock_get.side_effect = [
            (200, {'protected': True}),
            (200, {'required_pull_request_reviews': {'required_approving_review_count': 1}}),
        ]

        resp = self.api.post(f'/api/integrations/{self.integration_id}/sync/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(len(resp.data['results']), 2)
        self.assertTrue(all(r['passed'] for r in resp.data['results']))

        with schema_context(self.tenant.schema_name):
            from core.models import Control, Evidence
            from django.contrib.contenttypes.models import ContentType

            change_mgmt = Control.objects.get(identifier='A.8.32')
            secure_dev = Control.objects.get(identifier='A.8.25')
            self.assertEqual(change_mgmt.status, 'implemented')
            self.assertEqual(secure_dev.status, 'implemented')

            control_ct = ContentType.objects.get_for_model(Control)
            self.assertEqual(Evidence.objects.filter(content_type=control_ct, object_id=change_mgmt.id).count(), 1)
            self.assertIn('PASS', Evidence.objects.get(content_type=control_ct, object_id=change_mgmt.id).title)

    @patch('core.integrations.github.GitHubProvider._get')
    def test_sync_marks_controls_not_implemented_when_checks_fail(self, mock_get):
        mock_get.side_effect = [(200, {'protected': False})]

        resp = self.api.post(f'/api/integrations/{self.integration_id}/sync/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertFalse(resp.data['results'][0]['passed'])

        with schema_context(self.tenant.schema_name):
            from core.models import Control
            self.assertEqual(Control.objects.get(identifier='A.8.32').status, 'not_implemented')

    @patch('core.integrations.github.GitHubProvider._get')
    def test_sync_twice_creates_two_evidence_entries_not_one_overwritten(self, mock_get):
        mock_get.side_effect = [
            (200, {'protected': False}),
            (200, {'protected': True}),
            (200, {'required_pull_request_reviews': {}}),
        ]

        self.api.post(f'/api/integrations/{self.integration_id}/sync/', HTTP_HOST=self.host)
        self.api.post(f'/api/integrations/{self.integration_id}/sync/', HTTP_HOST=self.host)

        with schema_context(self.tenant.schema_name):
            from core.models import Control, Evidence, IntegrationCheckResult
            from django.contrib.contenttypes.models import ContentType

            control_ct = ContentType.objects.get_for_model(Control)
            change_mgmt = Control.objects.get(identifier='A.8.32')
            self.assertEqual(Evidence.objects.filter(content_type=control_ct, object_id=change_mgmt.id).count(), 2)
            self.assertEqual(IntegrationCheckResult.objects.filter(check_key='branch_protection').count(), 2)

    @patch('core.integrations.github.GitHubProvider._get')
    def test_a_bad_token_surfaces_as_a_clean_error_not_a_500(self, mock_get):
        mock_get.return_value = (401, {'message': 'Bad credentials'})

        resp = self.api.post(f'/api/integrations/{self.integration_id}/sync/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 400)
        self.assertIn('Bad credentials', resp.data['detail'])

        with schema_context(self.tenant.schema_name):
            from core.models import Integration
            integration = Integration.objects.get(pk=self.integration_id)
            self.assertEqual(integration.status, 'error')
            self.assertIn('Bad credentials', integration.last_error)

    @patch('core.integrations.github.GitHubProvider._get')
    def test_test_connection_action_does_not_touch_any_control(self, mock_get):
        mock_get.return_value = (200, {'login': 'acme-bot'})

        with schema_context(self.tenant.schema_name):
            from core.models import Control
            before = Control.objects.get(identifier='A.8.32').status

        resp = self.api.post(f'/api/integrations/{self.integration_id}/test-connection/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data['connected_as'], 'acme-bot')

        with schema_context(self.tenant.schema_name):
            from core.models import Control
            self.assertEqual(Control.objects.get(identifier='A.8.32').status, before)


class AWSSyncTests(TestCase):
    """Mocks boto3's S3 client (the one place AWSProvider talks to the
    network) the same way GitHubSyncTests mocks urllib."""

    def setUp(self):
        self.tenant = make_tenant('awssynctest')
        self.host = f'{self.tenant.schema_name}.localhost'
        self.admin = make_member(self.tenant, 'aws_admin', Membership.Role.ADMIN)
        with schema_context(self.tenant.schema_name):
            from core.models import Control
            Control.objects.create(framework='iso27001', identifier='A.8.24', name='Use of cryptography')
            Control.objects.create(framework='iso27001', identifier='A.8.3', name='Information access restriction')

        self.api = APIClient()
        self.api.force_authenticate(user=self.admin)
        create = self.api.post(
            '/api/integrations/',
            {
                'provider': 'aws', 'name': 'Acme S3',
                'config': {'bucket': 'acme-prod-data', 'region': 'us-east-1'},
                'credentials': {'access_key_id': 'AKIAFAKE', 'secret_access_key': 'fakefakefake'},
            },
            format='json', HTTP_HOST=self.host,
        )
        self.integration_id = create.data['id']

    @patch('core.integrations.aws.AWSProvider._client')
    def test_sync_passes_when_bucket_is_encrypted_and_locked_down(self, mock_client_factory):
        mock_client = MagicMock()
        mock_client.get_bucket_encryption.return_value = {
            'ServerSideEncryptionConfiguration': {'Rules': [{'ApplyServerSideEncryptionByDefault': {}}]},
        }
        mock_client.get_public_access_block.return_value = {
            'PublicAccessBlockConfiguration': {
                'BlockPublicAcls': True, 'IgnorePublicAcls': True,
                'BlockPublicPolicy': True, 'RestrictPublicBuckets': True,
            },
        }
        mock_client_factory.return_value = mock_client

        resp = self.api.post(f'/api/integrations/{self.integration_id}/sync/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertTrue(all(r['passed'] for r in resp.data['results']))

        with schema_context(self.tenant.schema_name):
            from core.models import Control
            self.assertEqual(Control.objects.get(identifier='A.8.24').status, 'implemented')
            self.assertEqual(Control.objects.get(identifier='A.8.3').status, 'implemented')

    @patch('core.integrations.aws.AWSProvider._client')
    def test_sync_fails_when_bucket_has_no_encryption_configured(self, mock_client_factory):
        from botocore.exceptions import ClientError

        mock_client = MagicMock()
        mock_client.get_bucket_encryption.side_effect = ClientError(
            {'Error': {'Code': 'ServerSideEncryptionConfigurationNotFoundError', 'Message': 'not found'}},
            'GetBucketEncryption',
        )
        mock_client.get_public_access_block.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchPublicAccessBlockConfiguration', 'Message': 'not found'}},
            'GetPublicAccessBlock',
        )
        mock_client_factory.return_value = mock_client

        resp = self.api.post(f'/api/integrations/{self.integration_id}/sync/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertFalse(any(r['passed'] for r in resp.data['results']))

        with schema_context(self.tenant.schema_name):
            from core.models import Control
            self.assertEqual(Control.objects.get(identifier='A.8.24').status, 'not_implemented')