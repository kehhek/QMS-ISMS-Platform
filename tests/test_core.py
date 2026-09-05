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

    def test_patching_status_via_the_api_does_not_bypass_the_approval_workflow(self):
        # Regression test: status used to be a plain writable serializer
        # field, so anyone with document-write access could PATCH straight
        # to "approved" without ever going through WorkflowStepViewSet's
        # password-verified electronic signature. It's read-only now —
        # settable only by the workflow completing (see core/views.py).
        tenant = make_tenant('coretestdocstatusbypass')
        with schema_context(tenant.schema_name):
            from django.contrib.auth import get_user_model
            from tenants.models import Membership
            from core.models import Document

            User = get_user_model()
            user = User.objects.create_user('doc_editor', 'de@example.com', 'pass12345')
            Membership.objects.create(user=user, tenant=tenant, role=Membership.Role.USER)
            doc = Document.objects.create(title='Policy', content='v1', status=Document.Status.DRAFT)

        api = APIClient()
        api.force_authenticate(user=user)
        resp = api.patch(
            f'/api/documents/{doc.pk}/', {'status': 'approved'},
            format='json', HTTP_HOST=f'{tenant.schema_name}.localhost',
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data['status'], 'draft')

        with schema_context(tenant.schema_name):
            doc.refresh_from_db()
            self.assertEqual(doc.status, Document.Status.DRAFT)


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
    def test_member_without_required_role_cannot_write_but_can_read(self):
        tenant = make_tenant('coretestpermdeny')
        with schema_context(tenant.schema_name):
            from django.contrib.auth import get_user_model
            from tenants.models import Membership
            User = get_user_model()
            user = User.objects.create_user('plain_user', 'plain@example.com', 'pass12345')
            Membership.objects.create(user=user, tenant=tenant, role=Membership.Role.USER)

        api = APIClient()
        api.force_authenticate(user=user)
        write_response = api.post(
            '/api/audits/', {'title': 'New audit'}, HTTP_HOST=f'{tenant.schema_name}.localhost',
        )
        self.assertEqual(write_response.status_code, 403)

        read_response = api.get('/api/documents/', HTTP_HOST=f'{tenant.schema_name}.localhost')
        self.assertEqual(read_response.status_code, 200)

    def test_auditor_role_can_create_audit(self):
        tenant = make_tenant('coretestpermallow')
        with schema_context(tenant.schema_name):
            from django.contrib.auth import get_user_model
            from tenants.models import Membership
            User = get_user_model()
            user = User.objects.create_user('auditor_user', 'auditor@example.com', 'pass12345')
            Membership.objects.create(user=user, tenant=tenant, role=Membership.Role.AUDITOR)

        api = APIClient()
        api.force_authenticate(user=user)
        response = api.post(
            '/api/audits/', {'title': 'New audit'}, HTTP_HOST=f'{tenant.schema_name}.localhost',
        )
        self.assertEqual(response.status_code, 201)

    def test_role_does_not_leak_across_tenants(self):
        # A user who is an Auditor in tenant A has no membership at all in
        # tenant B, so their role must not carry over — this is the exact
        # bug the old global-Django-Group RBAC had.
        tenant_a = make_tenant('coretestisoa')
        tenant_b = make_tenant('coretestisob')
        with schema_context(tenant_a.schema_name):
            from django.contrib.auth import get_user_model
            from tenants.models import Membership
            User = get_user_model()
            user = User.objects.create_user('cross_tenant_user', 'x@example.com', 'pass12345')
            Membership.objects.create(user=user, tenant=tenant_a, role=Membership.Role.AUDITOR)

        api = APIClient()
        api.force_authenticate(user=user)

        allowed = api.post(
            '/api/audits/', {'title': 'Tenant A audit'}, HTTP_HOST=f'{tenant_a.schema_name}.localhost',
        )
        self.assertEqual(allowed.status_code, 201)

        denied = api.post(
            '/api/audits/', {'title': 'Tenant B audit'}, HTTP_HOST=f'{tenant_b.schema_name}.localhost',
        )
        self.assertEqual(denied.status_code, 403)

    def test_unauthenticated_request_is_rejected(self):
        tenant = make_tenant('coretestpermanon')
        api = APIClient()
        response = api.get('/api/documents/', HTTP_HOST=f'{tenant.schema_name}.localhost')
        self.assertEqual(response.status_code, 401)
