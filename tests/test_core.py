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


class DocumentCategoryAndFileTests(TestCase):
    """Policy/SOP/Work Instruction categories and the optional PDF
    attachment — each category filters to its own tab (?category=), a
    document only ever shows up on one; the attached file is served back
    through an authenticated download action, never a raw storage URL."""

    def setUp(self):
        self.tenant = make_tenant('doccategoryfile')
        self.host = f'{self.tenant.schema_name}.localhost'
        with schema_context(self.tenant.schema_name):
            from django.contrib.auth import get_user_model
            from tenants.models import Membership
            User = get_user_model()
            self.user = User.objects.create_user('doccat_user', 'u@example.com', 'pass12345')
            Membership.objects.create(user=self.user, tenant=self.tenant, role=Membership.Role.USER)

        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def test_category_defaults_to_general(self):
        resp = self.api.post('/api/documents/', {'title': 'Untitled'}, format='json', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['category'], 'general')

    def test_filtering_by_category_only_returns_that_category(self):
        self.api.post('/api/documents/', {'title': 'A Policy', 'category': 'policy'}, format='json', HTTP_HOST=self.host)
        self.api.post('/api/documents/', {'title': 'An SOP', 'category': 'sop'}, format='json', HTTP_HOST=self.host)
        self.api.post('/api/documents/', {'title': 'A General Doc'}, format='json', HTTP_HOST=self.host)

        policies = self.api.get('/api/documents/?category=policy', HTTP_HOST=self.host)
        self.assertEqual(policies.data['count'], 1)
        self.assertEqual(policies.data['results'][0]['title'], 'A Policy')

        general = self.api.get('/api/documents/?category=general', HTTP_HOST=self.host)
        self.assertEqual(general.data['count'], 1)
        self.assertEqual(general.data['results'][0]['title'], 'A General Doc')

    def test_uploading_a_pdf_and_downloading_it_round_trips(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        pdf_bytes = b'%PDF-1.4 fake pdf content for testing'
        create = self.api.post(
            '/api/documents/',
            {'title': 'Access Control Policy', 'category': 'policy', 'file': SimpleUploadedFile('policy.pdf', pdf_bytes)},
            format='multipart', HTTP_HOST=self.host,
        )
        self.assertEqual(create.status_code, 201, create.data)
        self.assertEqual(create.data['file'], f'/api/documents/{create.data["id"]}/download/')

        download = self.api.get(create.data['file'], HTTP_HOST=self.host)
        self.assertEqual(download.status_code, 200)
        content = b''.join(download.streaming_content)
        self.assertEqual(content, pdf_bytes)

    def test_download_requires_tenant_membership(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.contrib.auth import get_user_model

        create = self.api.post(
            '/api/documents/',
            {'title': 'Policy', 'file': SimpleUploadedFile('p.pdf', b'content')},
            format='multipart', HTTP_HOST=self.host,
        )

        User = get_user_model()
        outsider = User.objects.create_user('doccat_outsider', 'o@example.com', 'pass12345')
        api = APIClient()
        api.force_authenticate(user=outsider)
        resp = api.get(create.data['file'], HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 403)

    def test_downloading_a_document_with_no_file_is_a_clean_404(self):
        create = self.api.post('/api/documents/', {'title': 'No file here'}, format='json', HTTP_HOST=self.host)
        resp = self.api.get(f'/api/documents/{create.data["id"]}/download/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 404)

    def test_replacing_a_file_bumps_the_version_and_creates_a_revision(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        create = self.api.post(
            '/api/documents/',
            {'title': 'Versioned Policy', 'file': SimpleUploadedFile('v1.pdf', b'version one')},
            format='multipart', HTTP_HOST=self.host,
        )
        doc_id = create.data['id']
        self.assertEqual(create.data['version'], 1)

        resp = self.api.patch(
            f'/api/documents/{doc_id}/', {'file': SimpleUploadedFile('v2.pdf', b'version two')},
            format='multipart', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data['version'], 2)

        with schema_context(self.tenant.schema_name):
            from core.models import DocumentRevision
            revision = DocumentRevision.objects.get(document_id=doc_id, version=1)
            self.assertTrue(revision.file)
            # The old file is still reachable at its own stored path —
            # not overwritten by the new upload.
            with revision.file.open('rb') as f:
                self.assertEqual(f.read(), b'version one')


class DocumentStatusTrackingTests(TestCase):
    """?status= filtering and the status-summary action — the concrete
    tooling for "which documents are Draft/In Review/Approved/Archived",
    on top of the per-row StatusBadge that already existed."""

    def setUp(self):
        self.tenant = make_tenant('docstatustracking')
        self.host = f'{self.tenant.schema_name}.localhost'
        with schema_context(self.tenant.schema_name):
            from django.contrib.auth import get_user_model
            from tenants.models import Membership
            User = get_user_model()
            self.user = User.objects.create_user('docstatus_user', 'u@example.com', 'pass12345')
            Membership.objects.create(user=self.user, tenant=self.tenant, role=Membership.Role.USER)

        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def _create(self, title, category='general', status=None):
        with schema_context(self.tenant.schema_name):
            from core.models import Document
            doc = Document.objects.create(title=title, category=category, owner=self.user)
            if status:
                doc.status = status
                doc.save(update_fields=['status'])
            return doc.id

    def test_filtering_by_status_only_returns_that_status(self):
        self._create('Draft doc', status='draft')
        self._create('In review doc', status='in_review')
        self._create('Approved doc', status='approved')

        resp = self.api.get('/api/documents/?status=approved', HTTP_HOST=self.host)
        self.assertEqual(resp.data['count'], 1)
        self.assertEqual(resp.data['results'][0]['title'], 'Approved doc')

    def test_status_summary_counts_every_status(self):
        self._create('Draft one', status='draft')
        self._create('Draft two', status='draft')
        self._create('In review one', status='in_review')
        self._create('Approved one', status='approved')
        self._create('Archived one', status='archived')

        resp = self.api.get('/api/documents/status-summary/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data, {'draft': 2, 'in_review': 1, 'approved': 1, 'archived': 1})

    def test_status_summary_scoped_to_category_but_ignores_status_filter(self):
        self._create('Policy draft', category='policy', status='draft')
        self._create('Policy approved', category='policy', status='approved')
        self._create('General draft', category='general', status='draft')

        resp = self.api.get('/api/documents/status-summary/?category=policy&status=draft', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 200, resp.data)
        # Ignores ?status= (always reports all four counts) but still
        # honors ?category= — only the two policy docs are counted.
        self.assertEqual(resp.data, {'draft': 1, 'in_review': 0, 'approved': 1, 'archived': 0})


class DocumentControlFieldsTests(TestCase):
    """Document ID, classification, and the reviewer/approver assignment
    fields — informational document-control metadata, distinct from the
    actual enforced e-signed approval (WorkflowStep/ElectronicSignature)."""

    def setUp(self):
        self.tenant = make_tenant('doccontrolfields')
        self.host = f'{self.tenant.schema_name}.localhost'
        with schema_context(self.tenant.schema_name):
            from django.contrib.auth import get_user_model
            from tenants.models import Membership
            User = get_user_model()
            self.author = User.objects.create_user('doc_author', 'a@example.com', 'pass12345')
            Membership.objects.create(user=self.author, tenant=self.tenant, role=Membership.Role.USER)
            self.reviewer = User.objects.create_user('doc_reviewer', 'r@example.com', 'pass12345')
            Membership.objects.create(user=self.reviewer, tenant=self.tenant, role=Membership.Role.USER)
            self.approver = User.objects.create_user('doc_approver', 'p@example.com', 'pass12345')
            Membership.objects.create(user=self.approver, tenant=self.tenant, role=Membership.Role.ADMIN)

        self.api = APIClient()
        self.api.force_authenticate(user=self.author)

    def test_create_sets_all_new_fields(self):
        resp = self.api.post(
            '/api/documents/',
            {
                'doc_id': 'QMS-001', 'title': 'Access Control Policy', 'classification': 'confidential',
                'reviewer': self.reviewer.pk, 'approver': self.approver.pk,
            },
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['doc_id'], 'QMS-001')
        self.assertEqual(resp.data['classification'], 'confidential')
        self.assertEqual(resp.data['reviewer_username'], 'doc_reviewer')
        self.assertEqual(resp.data['approver_username'], 'doc_approver')
        # Author defaults to the creator when not given.
        self.assertEqual(resp.data['owner_username'], 'doc_author')

    def test_classification_defaults_to_internal(self):
        resp = self.api.post('/api/documents/', {'title': 'Untitled Policy'}, format='json', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['classification'], 'internal')
        self.assertEqual(resp.data['doc_id'], '')

    def test_reviewer_and_approver_are_plainly_editable(self):
        # Distinct from `status`, which stays read-only — these are
        # informational assignment, not the enforced approval gate.
        create = self.api.post('/api/documents/', {'title': 'Policy'}, format='json', HTTP_HOST=self.host)
        doc_id = create.data['id']

        resp = self.api.patch(
            f'/api/documents/{doc_id}/', {'reviewer': self.reviewer.pk, 'approver': self.approver.pk},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data['reviewer_username'], 'doc_reviewer')
        self.assertEqual(resp.data['approver_username'], 'doc_approver')


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


class ControlAttachmentTests(TestCase):
    """Images/documents attached directly to a Control, via the same
    generic Evidence model everything else attaches to — the ?content_type=
    & ?object_id= filter is what lets the Controls page show just one
    control's own attachments instead of the whole flat Evidence tab."""

    def setUp(self):
        self.tenant = make_tenant('controlattachments')
        self.host = f'{self.tenant.schema_name}.localhost'
        with schema_context(self.tenant.schema_name):
            from django.contrib.auth import get_user_model
            from tenants.models import Membership
            from core.models import Control
            User = get_user_model()
            self.user = User.objects.create_user('ctrlattach_user', 'u@example.com', 'pass12345')
            Membership.objects.create(user=self.user, tenant=self.tenant, role=Membership.Role.USER)
            self.control_a = Control.objects.create(framework=Control.Framework.ISO27001, identifier='A.5.1', name='Policies')
            self.control_b = Control.objects.create(framework=Control.Framework.ISO27001, identifier='A.5.2', name='Roles')

            from django.contrib.contenttypes.models import ContentType
            self.control_ct = ContentType.objects.get_for_model(Control).id

        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def test_uploading_an_image_and_a_document_to_a_control_and_filtering_to_it(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        image = self.api.post(
            '/api/evidence/',
            {
                'title': 'Firewall screenshot', 'content_type': self.control_ct, 'object_id': self.control_a.id,
                'file': SimpleUploadedFile('shot.png', b'\x89PNG fake bytes', content_type='image/png'),
            },
            format='multipart', HTTP_HOST=self.host,
        )
        self.assertEqual(image.status_code, 201, image.data)

        doc = self.api.post(
            '/api/evidence/',
            {
                'title': 'Policy excerpt', 'content_type': self.control_ct, 'object_id': self.control_a.id,
                'file': SimpleUploadedFile('excerpt.pdf', b'%PDF-1.4 fake', content_type='application/pdf'),
            },
            format='multipart', HTTP_HOST=self.host,
        )
        self.assertEqual(doc.status_code, 201, doc.data)

        # Another control's own attachments filter must not leak in here.
        self.api.post(
            '/api/evidence/',
            {
                'title': 'Unrelated', 'content_type': self.control_ct, 'object_id': self.control_b.id,
                'file': SimpleUploadedFile('other.pdf', b'unrelated', content_type='application/pdf'),
            },
            format='multipart', HTTP_HOST=self.host,
        )

        resp = self.api.get(
            f'/api/evidence/?content_type={self.control_ct}&object_id={self.control_a.id}', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.data['count'], 2)
        titles = {r['title'] for r in resp.data['results']}
        self.assertEqual(titles, {'Firewall screenshot', 'Policy excerpt'})

    def test_downloading_an_attached_file_round_trips(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        create = self.api.post(
            '/api/evidence/',
            {
                'title': 'Screenshot', 'content_type': self.control_ct, 'object_id': self.control_a.id,
                'file': SimpleUploadedFile('shot.png', b'raw png bytes', content_type='image/png'),
            },
            format='multipart', HTTP_HOST=self.host,
        )
        download = self.api.get(create.data['file'], HTTP_HOST=self.host)
        self.assertEqual(download.status_code, 200)
        content = b''.join(download.streaming_content)
        self.assertEqual(content, b'raw png bytes')


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
