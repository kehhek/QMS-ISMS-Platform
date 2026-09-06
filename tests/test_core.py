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


class PolicyTemplateTests(TestCase):
    """Generating a starter Policy document from a bundled template — see
    core/data/policy_templates.py. Solves the blank-page problem; still a
    completely normal Document afterward (Draft, goes through the same
    approval workflow as one written from scratch)."""

    def setUp(self):
        self.tenant = make_tenant('policytemplates')
        self.host = f'{self.tenant.schema_name}.localhost'
        with schema_context(self.tenant.schema_name):
            from django.contrib.auth import get_user_model
            from tenants.models import Membership
            User = get_user_model()
            self.admin = User.objects.create_user('policytpl_admin', 'a@example.com', 'pass12345')
            Membership.objects.create(user=self.admin, tenant=self.tenant, role=Membership.Role.ADMIN)
            self.auditor = User.objects.create_user('policytpl_auditor', 'x@example.com', 'pass12345')
            Membership.objects.create(user=self.auditor, tenant=self.tenant, role=Membership.Role.AUDITOR)

        self.api = APIClient()
        self.api.force_authenticate(user=self.admin)

    def test_listing_templates_reports_every_bundled_template(self):
        from core.data.policy_templates import POLICY_TEMPLATES

        resp = self.api.get('/api/policy-templates/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), len(POLICY_TEMPLATES))
        self.assertTrue(all(not t['already_generated'] for t in resp.data))

    def test_generating_a_template_creates_a_draft_policy_document(self):
        resp = self.api.post('/api/policy-templates/access-control-policy/generate/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['category'], 'policy')
        self.assertEqual(resp.data['status'], 'draft')
        self.assertEqual(resp.data['title'], 'Access Control Policy')
        self.assertIn('PURPOSE', resp.data['content'])
        self.assertFalse(resp.data['already_existed'])

    def test_generating_the_same_template_twice_reuses_the_existing_document(self):
        first = self.api.post('/api/policy-templates/incident-response-policy/generate/', HTTP_HOST=self.host)
        second = self.api.post('/api/policy-templates/incident-response-policy/generate/', HTTP_HOST=self.host)
        self.assertEqual(first.data['id'], second.data['id'])
        self.assertTrue(second.data['already_existed'])

        with schema_context(self.tenant.schema_name):
            from core.models import Document
            self.assertEqual(Document.objects.filter(category='policy').count(), 1)

    def test_generated_policy_shows_up_in_the_policies_list(self):
        self.api.post('/api/policy-templates/data-classification-policy/generate/', HTTP_HOST=self.host)
        resp = self.api.get('/api/documents/?category=policy', HTTP_HOST=self.host)
        self.assertEqual(resp.data['count'], 1)
        self.assertEqual(resp.data['results'][0]['title'], 'Data Classification & Handling Policy')

    def test_unknown_template_slug_is_a_clean_404(self):
        resp = self.api.post('/api/policy-templates/does-not-exist/generate/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 404)

    def test_auditor_can_browse_but_not_generate(self):
        api = APIClient()
        api.force_authenticate(user=self.auditor)

        listing = api.get('/api/policy-templates/', HTTP_HOST=self.host)
        self.assertEqual(listing.status_code, 200)

        generate = api.post('/api/policy-templates/acceptable-use-policy/generate/', HTTP_HOST=self.host)
        self.assertEqual(generate.status_code, 403)


class SupplierQuestionnaireTests(TestCase):
    """Creating, sending, and publicly responding to a supplier
    questionnaire — the access_token in the public link is the supplier's
    only credential, so there's no login involved on their side at all."""

    def setUp(self):
        self.tenant = make_tenant('supplierquestionnaire')
        self.host = f'{self.tenant.schema_name}.localhost'
        with schema_context(self.tenant.schema_name):
            from django.contrib.auth import get_user_model
            from tenants.models import Membership
            from core.models import Supplier
            User = get_user_model()
            self.admin = User.objects.create_user('sq_admin', 'a@example.com', 'pass12345')
            Membership.objects.create(user=self.admin, tenant=self.tenant, role=Membership.Role.ADMIN)
            self.supplier = Supplier.objects.create(
                name='Acme Cloud', contact_name='Jane Vendor', contact_email='vendor@example.com',
            )

        self.api = APIClient()
        self.api.force_authenticate(user=self.admin)

    def _create_questionnaire(self):
        resp = self.api.post(
            '/api/supplier-questionnaires/',
            {'supplier': self.supplier.id, 'title': 'Annual Review', 'questions': ['Q1?', 'Q2?']},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        return resp.data

    def test_creating_a_questionnaire_generates_a_unique_access_token(self):
        data = self._create_questionnaire()
        self.assertEqual(data['status'], 'draft')
        self.assertTrue(data['access_token'])
        self.assertEqual(data['question_count'], 2)

    def test_sending_requires_a_contact_email_and_at_least_one_question(self):
        with schema_context(self.tenant.schema_name):
            from core.models import Supplier
            no_email_supplier = Supplier.objects.create(name='No Email Co')
        resp = self.api.post(
            '/api/supplier-questionnaires/',
            {'supplier': no_email_supplier.id, 'title': 'X', 'questions': ['Q1?']},
            format='json', HTTP_HOST=self.host,
        )
        send = self.api.post(f'/api/supplier-questionnaires/{resp.data["id"]}/send/', HTTP_HOST=self.host)
        self.assertEqual(send.status_code, 400)
        self.assertIn('contact email', send.data['detail'])

    def test_sending_emails_the_supplier_a_working_link(self):
        from django.core import mail

        data = self._create_questionnaire()
        send = self.api.post(f'/api/supplier-questionnaires/{data["id"]}/send/', HTTP_HOST=self.host)
        self.assertEqual(send.status_code, 200, send.data)
        self.assertEqual(send.data['status'], 'sent')
        self.assertEqual(send.data['sent_by_username'], 'sq_admin')

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['vendor@example.com'])
        self.assertIn(data['access_token'], mail.outbox[0].body)

    def test_supplier_can_view_and_submit_without_any_authentication(self):
        data = self._create_questionnaire()
        self.api.post(f'/api/supplier-questionnaires/{data["id"]}/send/', HTTP_HOST=self.host)
        token = data['access_token']

        anon = APIClient()
        view = anon.get(f'/api/public/questionnaires/{token}/', HTTP_HOST=self.host)
        self.assertEqual(view.status_code, 200)
        self.assertEqual(view.data['questions'], ['Q1?', 'Q2?'])
        self.assertFalse(view.data['already_responded'])

        submit = anon.post(
            f'/api/public/questionnaires/{token}/', {'answers': ['Yes', 'No']},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(submit.status_code, 200, submit.data)

        # Admin side sees the response land.
        detail = self.api.get(f'/api/supplier-questionnaires/{data["id"]}/', HTTP_HOST=self.host)
        self.assertEqual(detail.data['status'], 'responded')
        self.assertEqual(
            detail.data['responses'], [{'question': 'Q1?', 'answer': 'Yes'}, {'question': 'Q2?', 'answer': 'No'}],
        )

    def test_a_draft_questionnaire_is_not_publicly_reachable(self):
        data = self._create_questionnaire()  # never sent
        anon = APIClient()
        resp = anon.get(f'/api/public/questionnaires/{data["access_token"]}/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 404)

    def test_cannot_submit_the_same_questionnaire_twice(self):
        data = self._create_questionnaire()
        self.api.post(f'/api/supplier-questionnaires/{data["id"]}/send/', HTTP_HOST=self.host)
        token = data['access_token']
        anon = APIClient()
        anon.post(f'/api/public/questionnaires/{token}/', {'answers': ['A', 'B']}, format='json', HTTP_HOST=self.host)
        again = anon.post(f'/api/public/questionnaires/{token}/', {'answers': ['C', 'D']}, format='json', HTTP_HOST=self.host)
        self.assertEqual(again.status_code, 400)

    def test_wrong_number_of_answers_is_rejected(self):
        data = self._create_questionnaire()
        self.api.post(f'/api/supplier-questionnaires/{data["id"]}/send/', HTTP_HOST=self.host)
        anon = APIClient()
        resp = anon.post(
            f'/api/public/questionnaires/{data["access_token"]}/', {'answers': ['only one']},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 400)

    def test_reviewing_requires_a_response_first(self):
        data = self._create_questionnaire()
        self.api.post(f'/api/supplier-questionnaires/{data["id"]}/send/', HTTP_HOST=self.host)
        too_early = self.api.post(f'/api/supplier-questionnaires/{data["id"]}/review/', HTTP_HOST=self.host)
        self.assertEqual(too_early.status_code, 400)

    def test_reviewing_after_a_response_marks_it_reviewed(self):
        data = self._create_questionnaire()
        self.api.post(f'/api/supplier-questionnaires/{data["id"]}/send/', HTTP_HOST=self.host)
        anon = APIClient()
        anon.post(
            f'/api/public/questionnaires/{data["access_token"]}/', {'answers': ['A', 'B']},
            format='json', HTTP_HOST=self.host,
        )
        review = self.api.post(f'/api/supplier-questionnaires/{data["id"]}/review/', HTTP_HOST=self.host)
        self.assertEqual(review.status_code, 200, review.data)
        self.assertEqual(review.data['status'], 'reviewed')
        self.assertEqual(review.data['reviewed_by_username'], 'sq_admin')

    def test_auditor_can_read_but_not_create_or_send(self):
        with schema_context(self.tenant.schema_name):
            from django.contrib.auth import get_user_model
            from tenants.models import Membership
            User = get_user_model()
            auditor = User.objects.create_user('sq_auditor', 'x@example.com', 'pass12345')
            Membership.objects.create(user=auditor, tenant=self.tenant, role=Membership.Role.AUDITOR)

        api = APIClient()
        api.force_authenticate(user=auditor)
        listing = api.get('/api/supplier-questionnaires/', HTTP_HOST=self.host)
        self.assertEqual(listing.status_code, 200)

        create = api.post(
            '/api/supplier-questionnaires/', {'supplier': self.supplier.id, 'title': 'X', 'questions': ['Q?']},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(create.status_code, 403)

    def _respond(self, data):
        anon = APIClient()
        return anon.post(
            f'/api/public/questionnaires/{data["access_token"]}/', {'answers': ['A', 'B']},
            format='json', HTTP_HOST=self.host,
        )

    def test_approving_moves_supplier_to_active_and_emails_them(self):
        from django.core import mail

        data = self._create_questionnaire()
        self.api.post(f'/api/supplier-questionnaires/{data["id"]}/send/', HTTP_HOST=self.host)
        self._respond(data)

        resp = self.api.post(f'/api/supplier-questionnaires/{data["id"]}/approve/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data['status'], 'approved')
        self.assertEqual(resp.data['decided_by_username'], 'sq_admin')
        self.assertIsNotNone(resp.data['decided_at'])

        self.supplier.refresh_from_db()
        self.assertEqual(self.supplier.status, 'active')

        self.assertEqual(len(mail.outbox), 2)  # send + approve
        self.assertIn('approved', mail.outbox[-1].subject.lower())

    def test_rejecting_does_not_touch_supplier_status(self):
        data = self._create_questionnaire()
        self.api.post(f'/api/supplier-questionnaires/{data["id"]}/send/', HTTP_HOST=self.host)
        self._respond(data)

        original_status = self.supplier.status
        resp = self.api.post(f'/api/supplier-questionnaires/{data["id"]}/reject/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data['status'], 'rejected')

        self.supplier.refresh_from_db()
        self.assertEqual(self.supplier.status, original_status)

    def test_cannot_approve_before_the_supplier_has_responded(self):
        data = self._create_questionnaire()
        self.api.post(f'/api/supplier-questionnaires/{data["id"]}/send/', HTTP_HOST=self.host)
        resp = self.api.post(f'/api/supplier-questionnaires/{data["id"]}/approve/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 400)

    def test_can_approve_after_marking_reviewed_too(self):
        data = self._create_questionnaire()
        self.api.post(f'/api/supplier-questionnaires/{data["id"]}/send/', HTTP_HOST=self.host)
        self._respond(data)
        self.api.post(f'/api/supplier-questionnaires/{data["id"]}/review/', HTTP_HOST=self.host)
        resp = self.api.post(f'/api/supplier-questionnaires/{data["id"]}/approve/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 200, resp.data)


class SupplierAgreementTests(TestCase):
    """Sending a vendor agreement for e-signature once a supplier is
    approved — same no-account public-link pattern as the questionnaire,
    with a typed name/title standing in for ElectronicSignature (which
    needs a real user account this external party doesn't have)."""

    def setUp(self):
        self.tenant = make_tenant('supplieragreement')
        self.host = f'{self.tenant.schema_name}.localhost'
        with schema_context(self.tenant.schema_name):
            from django.contrib.auth import get_user_model
            from tenants.models import Membership
            from core.models import Supplier
            User = get_user_model()
            self.admin = User.objects.create_user('sa_admin', 'a@example.com', 'pass12345')
            Membership.objects.create(user=self.admin, tenant=self.tenant, role=Membership.Role.ADMIN)
            self.supplier = Supplier.objects.create(
                name='Acme Cloud', contact_name='Jane Vendor', contact_email='vendor@example.com',
            )

        self.api = APIClient()
        self.api.force_authenticate(user=self.admin)

    def _create_agreement(self, **extra):
        payload = {'supplier': self.supplier.id, 'title': 'Vendor Agreement', 'content': 'Standard terms.'}
        payload.update(extra)
        resp = self.api.post('/api/supplier-agreements/', payload, format='json', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 201, resp.data)
        return resp.data

    def test_sending_emails_the_supplier_a_working_link(self):
        from django.core import mail

        data = self._create_agreement()
        resp = self.api.post(f'/api/supplier-agreements/{data["id"]}/send/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data['status'], 'sent')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(data['access_token'], mail.outbox[0].body)

    def test_supplier_can_view_and_sign_without_any_authentication(self):
        data = self._create_agreement()
        self.api.post(f'/api/supplier-agreements/{data["id"]}/send/', HTTP_HOST=self.host)
        token = data['access_token']

        anon = APIClient()
        view = anon.get(f'/api/public/agreements/{token}/', HTTP_HOST=self.host)
        self.assertEqual(view.status_code, 200)
        self.assertFalse(view.data['already_signed'])

        sign = anon.post(
            f'/api/public/agreements/{token}/', {'signer_name': 'Jane Vendor', 'signer_title': 'VP Sales'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(sign.status_code, 200, sign.data)

        detail = self.api.get(f'/api/supplier-agreements/{data["id"]}/', HTTP_HOST=self.host)
        self.assertEqual(detail.data['status'], 'signed')
        self.assertEqual(detail.data['signer_name'], 'Jane Vendor')
        self.assertEqual(detail.data['signer_title'], 'VP Sales')
        self.assertIsNotNone(detail.data['signed_at'])

    def test_a_draft_agreement_is_not_publicly_reachable(self):
        data = self._create_agreement()  # never sent
        anon = APIClient()
        resp = anon.get(f'/api/public/agreements/{data["access_token"]}/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 404)

    def test_cannot_sign_twice(self):
        data = self._create_agreement()
        self.api.post(f'/api/supplier-agreements/{data["id"]}/send/', HTTP_HOST=self.host)
        token = data['access_token']
        anon = APIClient()
        anon.post(f'/api/public/agreements/{token}/', {'signer_name': 'A'}, format='json', HTTP_HOST=self.host)
        again = anon.post(f'/api/public/agreements/{token}/', {'signer_name': 'B'}, format='json', HTTP_HOST=self.host)
        self.assertEqual(again.status_code, 400)

    def test_signing_without_a_name_is_rejected(self):
        data = self._create_agreement()
        self.api.post(f'/api/supplier-agreements/{data["id"]}/send/', HTTP_HOST=self.host)
        anon = APIClient()
        resp = anon.post(
            f'/api/public/agreements/{data["access_token"]}/', {'signer_name': ''},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 400)

    def test_uploaded_file_is_downloadable_via_the_public_token_route(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        create = self.api.post(
            '/api/supplier-agreements/',
            {
                'supplier': self.supplier.id, 'title': 'PDF Agreement',
                'file': SimpleUploadedFile('agreement.pdf', b'%PDF-1.4 fake', content_type='application/pdf'),
            },
            format='multipart', HTTP_HOST=self.host,
        )
        self.assertEqual(create.status_code, 201, create.data)
        self.api.post(f'/api/supplier-agreements/{create.data["id"]}/send/', HTTP_HOST=self.host)

        # The public GET must NOT point at the authenticated download
        # action (that 403s an external supplier with no account).
        public = APIClient().get(f'/api/public/agreements/{create.data["access_token"]}/', HTTP_HOST=self.host)
        self.assertTrue(public.data['file'].startswith('/api/public/agreements/'))

        download = APIClient().get(public.data['file'], HTTP_HOST=self.host)
        self.assertEqual(download.status_code, 200)
        content = b''.join(download.streaming_content)
        self.assertEqual(content, b'%PDF-1.4 fake')


class PublicTrustCenterTests(TestCase):
    """The public, no-login Trust Center page — only aggregate figures,
    never individual control/risk/incident detail."""

    def setUp(self):
        self.tenant = make_tenant('trustcenter')
        self.host = f'{self.tenant.schema_name}.localhost'

    def test_reports_aggregate_framework_percentages(self):
        with schema_context(self.tenant.schema_name):
            from core.models import Control, Document
            Control.objects.create(framework='iso27001', identifier='A.1', name='x', status='implemented')
            Control.objects.create(framework='iso27001', identifier='A.2', name='y', status='not_implemented')
            Control.objects.create(framework='iso27001', identifier='A.3', name='z', status='not_implemented')
            Control.objects.create(framework='soc2', identifier='CC1.1', name='a', status='implemented')
            Document.objects.create(title='Policy A', category='policy', status='approved')
            Document.objects.create(title='Policy B', category='policy', status='draft')

        anon = APIClient()
        resp = anon.get('/api/public/trust-center/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data['org_name'], self.tenant.name)
        self.assertEqual(resp.data['frameworks']['iso27001'], {'total': 3, 'implemented': 1, 'percent': 33})
        self.assertEqual(resp.data['frameworks']['soc2'], {'total': 1, 'implemented': 1, 'percent': 100})
        # Only the approved one counts — a draft policy isn't "published".
        self.assertEqual(resp.data['published_policies'], 1)

    def test_never_exposes_control_level_or_risk_detail(self):
        anon = APIClient()
        resp = anon.get('/api/public/trust-center/', HTTP_HOST=self.host)
        body_str = str(resp.data)
        for leaky_key in ('risks', 'incidents', 'controls', 'documents'):
            self.assertNotIn(leaky_key, resp.data)


class AuditorAccessTests(TestCase):
    """A scoped, time-boxed, read-only link for an external auditor — no
    account needed, same no-account public-link pattern as the supplier
    questionnaire/agreement flows. Framework scoping and expiry/
    revocation are the actual security boundary here, so those get the
    most coverage."""

    def setUp(self):
        self.tenant = make_tenant('auditoraccesstest')
        self.host = f'{self.tenant.schema_name}.localhost'
        with schema_context(self.tenant.schema_name):
            from django.contrib.auth import get_user_model
            from tenants.models import Membership
            from core.models import Control, Evidence, Document
            from django.contrib.contenttypes.models import ContentType

            User = get_user_model()
            self.admin = User.objects.create_user('aa_admin', 'a@example.com', 'pass12345')
            Membership.objects.create(user=self.admin, tenant=self.tenant, role=Membership.Role.ADMIN)
            self.auditor_role_user = User.objects.create_user('aa_auditor', 'x@example.com', 'pass12345')
            Membership.objects.create(user=self.auditor_role_user, tenant=self.tenant, role=Membership.Role.AUDITOR)
            self.plain_user = User.objects.create_user('aa_user', 'u@example.com', 'pass12345')
            Membership.objects.create(user=self.plain_user, tenant=self.tenant, role=Membership.Role.USER)

            self.iso_control = Control.objects.create(
                framework='iso27001', identifier='A.5.1', name='Policies', status='implemented',
            )
            self.soc2_control = Control.objects.create(framework='soc2', identifier='CC1.1', name='Integrity')
            control_ct = ContentType.objects.get_for_model(Control)

            from django.core.files.uploadedfile import SimpleUploadedFile
            self.iso_evidence = Evidence.objects.create(
                title='Screenshot', content_type=control_ct, object_id=self.iso_control.id,
                file=SimpleUploadedFile('shot.png', b'iso evidence bytes'),
            )
            self.soc2_evidence = Evidence.objects.create(
                title='SOC2 doc', content_type=control_ct, object_id=self.soc2_control.id,
                file=SimpleUploadedFile('soc2.txt', b'soc2 evidence bytes'),
            )
            self.approved_policy = Document.objects.create(
                title='Security Policy', category='policy', status='approved',
                file=SimpleUploadedFile('policy.pdf', b'%PDF-1.4 fake'),
            )
            Document.objects.create(title='Draft Policy', category='policy', status='draft')

        self.api = APIClient()
        self.api.force_authenticate(user=self.admin)

    def _create_access(self, **extra):
        from django.utils import timezone
        import datetime

        payload = {
            'title': 'ISO 27001 Audit', 'framework': 'iso27001',
            'expires_at': (timezone.now() + datetime.timedelta(days=7)).isoformat(),
        }
        payload.update(extra)
        resp = self.api.post('/api/auditor-access/', payload, format='json', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 201, resp.data)
        return resp.data

    def test_only_admin_can_create_a_link(self):
        auditor_api = APIClient()
        auditor_api.force_authenticate(user=self.auditor_role_user)
        resp = auditor_api.post(
            '/api/auditor-access/', {'title': 'x', 'expires_at': '2099-01-01T00:00:00Z'},
            format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 403)

    def test_plain_user_cannot_even_list_links(self):
        user_api = APIClient()
        user_api.force_authenticate(user=self.plain_user)
        resp = user_api.get('/api/auditor-access/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 403)

    def test_auditor_role_can_view_but_not_create(self):
        auditor_api = APIClient()
        auditor_api.force_authenticate(user=self.auditor_role_user)
        listing = auditor_api.get('/api/auditor-access/', HTTP_HOST=self.host)
        self.assertEqual(listing.status_code, 200)

    def test_the_public_link_is_scoped_to_its_framework(self):
        data = self._create_access(framework='iso27001')
        anon = APIClient()
        resp = anon.get(f'/api/public/auditor-access/{data["access_token"]}/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 200, resp.data)
        frameworks = {c['framework'] for c in resp.data['controls']}
        self.assertEqual(frameworks, {'iso27001'})

        control = next(c for c in resp.data['controls'] if c['id'] == self.iso_control.id)
        self.assertEqual(len(control['evidence']), 1)
        self.assertEqual(control['evidence'][0]['title'], 'Screenshot')

    def test_only_approved_policies_are_exposed(self):
        data = self._create_access()
        anon = APIClient()
        resp = anon.get(f'/api/public/auditor-access/{data["access_token"]}/', HTTP_HOST=self.host)
        titles = {p['title'] for p in resp.data['policies']}
        self.assertEqual(titles, {'Security Policy'})

    def test_cannot_reach_evidence_outside_the_frameworks_scope(self):
        data = self._create_access(framework='iso27001')
        anon = APIClient()
        # The soc2 control's own evidence must 404 even though the token
        # is otherwise valid — scoping is enforced per-file, not just on
        # the summary payload.
        resp = anon.get(
            f'/api/public/auditor-access/{data["access_token"]}/evidence/{self.soc2_evidence.id}/',
            HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 404)

    def test_evidence_and_policy_files_round_trip(self):
        data = self._create_access()
        anon = APIClient()
        ev_resp = anon.get(
            f'/api/public/auditor-access/{data["access_token"]}/evidence/{self.iso_evidence.id}/',
            HTTP_HOST=self.host,
        )
        self.assertEqual(ev_resp.status_code, 200)
        self.assertEqual(b''.join(ev_resp.streaming_content), b'iso evidence bytes')

        policy_resp = anon.get(
            f'/api/public/auditor-access/{data["access_token"]}/policies/{self.approved_policy.id}/',
            HTTP_HOST=self.host,
        )
        self.assertEqual(policy_resp.status_code, 200)
        self.assertEqual(b''.join(policy_resp.streaming_content), b'%PDF-1.4 fake')

    def test_expired_link_is_not_reachable(self):
        from django.utils import timezone
        import datetime

        data = self._create_access(expires_at=(timezone.now() + datetime.timedelta(seconds=1)).isoformat())
        import time
        time.sleep(2)
        anon = APIClient()
        resp = anon.get(f'/api/public/auditor-access/{data["access_token"]}/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 404)

    def test_revoking_kills_access_immediately(self):
        data = self._create_access()
        revoke = self.api.post(f'/api/auditor-access/{data["id"]}/revoke/', HTTP_HOST=self.host)
        self.assertEqual(revoke.status_code, 200, revoke.data)
        self.assertFalse(revoke.data['is_active'])

        anon = APIClient()
        resp = anon.get(f'/api/public/auditor-access/{data["access_token"]}/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 404)

    def test_visiting_the_link_records_last_accessed_at(self):
        data = self._create_access()
        self.assertIsNone(data['last_accessed_at'])

        anon = APIClient()
        anon.get(f'/api/public/auditor-access/{data["access_token"]}/', HTTP_HOST=self.host)

        detail = self.api.get(f'/api/auditor-access/{data["id"]}/', HTTP_HOST=self.host)
        self.assertIsNotNone(detail.data['last_accessed_at'])
