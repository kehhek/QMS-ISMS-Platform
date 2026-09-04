from django.db import connection
from django.test import TestCase
from rest_framework.test import APIClient

from tenants.models import Client, Domain
from django_tenants.utils import schema_context


def make_tenant(schema_name):
    # A prior test's APIClient request may have left the connection set to
    # that tenant's schema (TenantMainMiddleware doesn't reset it after the
    # response) — creating a tenant requires starting from the public schema.
    connection.set_schema_to_public()
    client = Client.objects.create(schema_name=schema_name, name=schema_name)
    Domain.objects.create(domain=f'{schema_name}.localhost', tenant=client, is_primary=True)
    return client


class DocumentVersioningTests(TestCase):
    def test_editing_a_document_creates_a_revision_and_bumps_version(self):
        tenant = make_tenant('coretestdocver')
        with schema_context(tenant.schema_name):
            from core.models import Document, DocumentRevision

            doc = Document.objects.create(title='Policy', content='v1 text')
            self.assertEqual(doc.version, 1)
            self.assertEqual(DocumentRevision.objects.count(), 0)

            doc.content = 'v2 text'
            doc.save()
            doc.refresh_from_db()

            self.assertEqual(doc.version, 2)
            self.assertEqual(DocumentRevision.objects.count(), 1)
            revision = DocumentRevision.objects.first()
            self.assertEqual(revision.version, 1)
            self.assertEqual(revision.content, 'v1 text')

    def test_saving_without_changes_does_not_create_a_revision(self):
        tenant = make_tenant('coretestdocvernochange')
        with schema_context(tenant.schema_name):
            from core.models import Document, DocumentRevision

            doc = Document.objects.create(title='Policy', content='same text')
            doc.save()  # no field changes

            self.assertEqual(doc.version, 1)
            self.assertEqual(DocumentRevision.objects.count(), 0)


class CorrectiveActionTests(TestCase):
    def test_corrective_action_links_to_audit_and_risk(self):
        tenant = make_tenant('coretestcapa')
        with schema_context(tenant.schema_name):
            from core.models import Audit, Risk, CorrectiveAction

            audit = Audit.objects.create(title='Internal Audit')
            risk = Risk.objects.create(name='Test risk')
            action = CorrectiveAction.objects.create(title='Fix it', audit=audit, risk=risk)

            self.assertEqual(action.audit, audit)
            self.assertEqual(action.risk, risk)
            self.assertEqual(action.status, CorrectiveAction.Status.OPEN)


class CoreApiPermissionTests(TestCase):
    def test_authenticated_user_without_group_cannot_create_audit(self):
        tenant = make_tenant('coretestpermdeny')
        with schema_context(tenant.schema_name):
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.create_user('plain_user', 'plain@example.com', 'pass12345')

        api = APIClient()
        api.force_authenticate(user=user)
        response = api.post(
            '/api/audits/', {'title': 'New audit'}, HTTP_HOST=f'{tenant.schema_name}.localhost',
        )
        self.assertEqual(response.status_code, 403)

    def test_group_member_can_create_audit(self):
        tenant = make_tenant('coretestpermallow')
        with schema_context(tenant.schema_name):
            from django.contrib.auth import get_user_model
            from django.contrib.auth.models import Group
            User = get_user_model()
            user = User.objects.create_user('auditor_user', 'auditor@example.com', 'pass12345')
            group, _ = Group.objects.get_or_create(name='Auditors')
            user.groups.add(group)

        api = APIClient()
        api.force_authenticate(user=user)
        response = api.post(
            '/api/audits/', {'title': 'New audit'}, HTTP_HOST=f'{tenant.schema_name}.localhost',
        )
        self.assertEqual(response.status_code, 201)

    def test_unauthenticated_request_is_rejected(self):
        tenant = make_tenant('coretestpermanon')
        api = APIClient()
        response = api.get('/api/documents/', HTTP_HOST=f'{tenant.schema_name}.localhost')
        self.assertEqual(response.status_code, 401)
