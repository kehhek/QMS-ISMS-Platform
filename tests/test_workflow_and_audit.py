import tempfile

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from tenants.models import Client, Domain, Membership

User = get_user_model()


def make_tenant(schema_name):
    connection.set_schema_to_public()
    client = Client.objects.create(schema_name=schema_name, name=schema_name)
    Domain.objects.create(domain=f'{schema_name}.localhost', tenant=client, is_primary=True)
    return client


def make_member(tenant, username, role):
    user = User.objects.create_user(username, f'{username}@example.com', 'pass12345')
    Membership.objects.create(user=user, tenant=tenant, role=role)
    return user


class WorkflowApprovalTests(TestCase):
    def setUp(self):
        self.tenant = make_tenant('wftestflow')
        self.admin = make_member(self.tenant, 'wf_admin', Membership.Role.ADMIN)
        self.auditor = make_member(self.tenant, 'wf_auditor', Membership.Role.AUDITOR)
        self.plain_user = make_member(self.tenant, 'wf_user', Membership.Role.USER)

        from django_tenants.utils import schema_context
        with schema_context(self.tenant.schema_name):
            from core.models import Document
            self.document = Document.objects.create(title='Policy Draft', content='v1')

        self.host = f'{self.tenant.schema_name}.localhost'

    def _api_as(self, user):
        api = APIClient()
        api.force_authenticate(user=user)
        return api

    def _create_workflow(self):
        api = self._api_as(self.admin)
        resp = api.post(
            '/api/workflows/',
            {
                'document': self.document.pk,
                'new_steps': [
                    {'order': 1, 'approver_role': 'auditor'},
                    {'order': 2, 'approver_role': 'admin'},
                ],
            },
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        return resp.data

    def test_steps_must_be_decided_in_order(self):
        workflow = self._create_workflow()
        step_2_id = workflow['steps'][1]['id']

        api = self._api_as(self.admin)
        resp = api.post(f'/api/workflow-steps/{step_2_id}/decide/', {'decision': 'approved'}, HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 400)

    def test_wrong_role_cannot_decide_a_step(self):
        workflow = self._create_workflow()
        step_1_id = workflow['steps'][0]['id']

        api = self._api_as(self.plain_user)
        resp = api.post(f'/api/workflow-steps/{step_1_id}/decide/', {'decision': 'approved'}, HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 403)

    def test_full_approval_approves_document_and_logs_actions(self):
        workflow = self._create_workflow()
        step_1_id = workflow['steps'][0]['id']
        step_2_id = workflow['steps'][1]['id']

        api_auditor = self._api_as(self.auditor)
        resp = api_auditor.post(
            f'/api/workflow-steps/{step_1_id}/decide/',
            {'decision': 'approved', 'password': 'pass12345'}, HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 200, resp.data)

        api_admin = self._api_as(self.admin)
        resp = api_admin.post(
            f'/api/workflow-steps/{step_2_id}/decide/',
            {'decision': 'approved', 'password': 'pass12345'}, HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 200, resp.data)

        from django_tenants.utils import schema_context
        with schema_context(self.tenant.schema_name):
            from core.models import Document, Workflow, AuditLog
            self.document.refresh_from_db()
            self.assertEqual(self.document.status, Document.Status.APPROVED)
            self.assertEqual(self.document.version, 2)

            wf = Workflow.objects.get(pk=workflow['id'])
            self.assertEqual(wf.status, Workflow.Status.APPROVED)
            self.assertIsNotNone(wf.completed_at)

            approve_logs = AuditLog.objects.filter(action=AuditLog.Action.APPROVE)
            self.assertEqual(approve_logs.count(), 2)

    def test_rejection_stops_the_workflow(self):
        workflow = self._create_workflow()
        step_1_id = workflow['steps'][0]['id']

        api_auditor = self._api_as(self.auditor)
        resp = api_auditor.post(
            f'/api/workflow-steps/{step_1_id}/decide/',
            {'decision': 'rejected', 'comment': 'Needs more detail', 'password': 'pass12345'}, HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 200, resp.data)

        from django_tenants.utils import schema_context
        with schema_context(self.tenant.schema_name):
            from core.models import Workflow
            wf = Workflow.objects.get(pk=workflow['id'])
            self.assertEqual(wf.status, Workflow.Status.REJECTED)


class AuditLogImmutabilityTests(TestCase):
    def test_existing_log_entry_cannot_be_saved_again(self):
        tenant = make_tenant('wftestauditlog')
        from django_tenants.utils import schema_context
        with schema_context(tenant.schema_name):
            from core.models import AuditLog, Document
            from django.contrib.contenttypes.models import ContentType

            doc = Document.objects.create(title='Doc')
            log = AuditLog.objects.create(
                action=AuditLog.Action.CREATE,
                content_type=ContentType.objects.get_for_model(doc),
                object_id=doc.pk,
                target_repr='Doc',
            )
            log.action = AuditLog.Action.DELETE
            with self.assertRaises(ValueError):
                log.save()

    def test_existing_log_entry_cannot_be_deleted(self):
        tenant = make_tenant('wftestauditlogdel')
        from django_tenants.utils import schema_context
        with schema_context(tenant.schema_name):
            from core.models import AuditLog, Document
            from django.contrib.contenttypes.models import ContentType

            doc = Document.objects.create(title='Doc')
            log = AuditLog.objects.create(
                action=AuditLog.Action.CREATE,
                content_type=ContentType.objects.get_for_model(doc),
                object_id=doc.pk,
                target_repr='Doc',
            )
            with self.assertRaises(ValueError):
                log.delete()


class EvidenceGenericAttachmentTests(TestCase):
    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_evidence_can_attach_to_an_incident(self):
        tenant = make_tenant('wftestevidence')
        from django_tenants.utils import schema_context
        from django.core.files.uploadedfile import SimpleUploadedFile

        with schema_context(tenant.schema_name):
            from core.models import Incident, Evidence
            from django.contrib.contenttypes.models import ContentType

            incident = Incident.objects.create(title='Suspicious login')
            evidence = Evidence.objects.create(
                title='Server log excerpt',
                file=SimpleUploadedFile('log.txt', b'suspicious activity detected'),
                content_type=ContentType.objects.get_for_model(incident),
                object_id=incident.pk,
            )
            self.assertEqual(evidence.content_object, incident)
            self.assertEqual(incident.corrective_actions.count(), 0)  # sanity: unrelated reverse relation untouched
