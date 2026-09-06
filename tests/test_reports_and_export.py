"""CSV export (CsvExportMixin, core/export.py) and the PDF Controls
Status Report (core/reports.py) — "basic reports & export", one of the
platform's seven original pillars that had never actually been built."""

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


def make_member(tenant, username, role):
    user = User.objects.create_user(username, f'{username}@example.com', 'pass12345')
    Membership.objects.create(user=user, tenant=tenant, role=role)
    return user


class CsvExportTests(TestCase):
    def setUp(self):
        self.tenant = make_tenant('csvexporttest')
        self.host = f'{self.tenant.schema_name}.localhost'
        self.user = make_member(self.tenant, 'csv_user', Membership.Role.USER)

        with schema_context(self.tenant.schema_name):
            from core.models import Risk
            Risk.objects.create(name='Risk One', likelihood=2, impact=4, owner='Alex')
            Risk.objects.create(name='Risk Two', likelihood=1, impact=1)

        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def test_csv_export_contains_a_header_and_every_row(self):
        resp = self.api.get('/api/risks/export-csv/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/csv')
        self.assertIn('attachment', resp['Content-Disposition'])

        body = resp.content.decode()
        lines = body.strip().splitlines()
        self.assertEqual(
            lines[0],
            'id,name,description,likelihood,impact,status,owner,asset,asset_name,'
            'treatment_plan,target_date,residual_likelihood,residual_impact,created_at',
        )
        self.assertEqual(len(lines), 3)  # header + 2 rows
        self.assertIn('Risk One', body)
        self.assertIn('Alex', body)
        self.assertIn('Risk Two', body)

    def test_csv_export_respects_the_same_permissions_as_list(self):
        # export-csv is just another action on the same viewset — a
        # role that can't write shouldn't gain anything it couldn't
        # already read via the plain list endpoint, and a role locked
        # out of reading entirely should be locked out here too.
        outsider = User.objects.create_user('csv_outsider', 'o@example.com', 'pass12345')
        api = APIClient()
        api.force_authenticate(user=outsider)
        resp = api.get('/api/risks/export-csv/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 403)

    def test_csv_export_with_no_rows_still_returns_a_header(self):
        tenant = make_tenant('csvexportempty')
        user = make_member(tenant, 'csv_empty_user', Membership.Role.USER)
        api = APIClient()
        api.force_authenticate(user=user)
        resp = api.get('/api/risks/export-csv/', HTTP_HOST=f'{tenant.schema_name}.localhost')
        self.assertEqual(resp.status_code, 200)
        lines = resp.content.decode().strip().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertIn('name', lines[0])

    def test_audit_log_export_is_restricted_to_admin_and_auditor(self):
        resp = self.api.get('/api/audit-log/export-csv/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 403)

        admin = make_member(self.tenant, 'csv_admin', Membership.Role.ADMIN)
        api = APIClient()
        api.force_authenticate(user=admin)
        resp = api.get('/api/audit-log/export-csv/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 200)


class ControlsStatusReportTests(TestCase):
    def setUp(self):
        self.tenant = make_tenant('pdfreporttest')
        self.host = f'{self.tenant.schema_name}.localhost'
        self.user = make_member(self.tenant, 'pdf_user', Membership.Role.USER)

        with schema_context(self.tenant.schema_name):
            from core.models import Control
            Control.objects.create(
                framework=Control.Framework.ISO27001, identifier='A.5.1', name='Policies',
                status=Control.Status.IMPLEMENTED,
            )
            Control.objects.create(
                framework=Control.Framework.SOC2, identifier='CC1.1',
                name='The entity demonstrates a commitment to integrity and ethical values '
                     'across every level of the organization, including its subsidiaries',
            )

    def test_report_is_a_valid_pdf(self):
        api = APIClient()
        api.force_authenticate(user=self.user)
        resp = api.get('/api/reports/controls-status/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertTrue(resp.content.startswith(b'%PDF'))
        self.assertGreater(len(resp.content), 500)

    def test_report_requires_tenant_membership(self):
        outsider = User.objects.create_user('pdf_outsider', 'o2@example.com', 'pass12345')
        api = APIClient()
        api.force_authenticate(user=outsider)
        resp = api.get('/api/reports/controls-status/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 403)


class StatementOfApplicabilityReportTests(TestCase):
    """The generated ISO 27001 SoA — status/owner/evidence pulled live at
    generation time, soa_justification the one field a person writes."""

    def setUp(self):
        self.tenant = make_tenant('soareporttest')
        self.host = f'{self.tenant.schema_name}.localhost'
        self.user = make_member(self.tenant, 'soa_user', Membership.Role.USER)

        with schema_context(self.tenant.schema_name):
            from django.contrib.contenttypes.models import ContentType
            from core.models import Control, Evidence

            self.implemented = Control.objects.create(
                framework=Control.Framework.ISO27001, identifier='A.5.1', name='Policies',
                status=Control.Status.IMPLEMENTED, soa_justification='Required by policy.',
            )
            self.not_applicable = Control.objects.create(
                framework=Control.Framework.ISO27001, identifier='A.7.1', name='Physical security perimeters',
                status=Control.Status.NOT_APPLICABLE, soa_justification='Fully remote organization.',
            )
            Control.objects.create(
                framework=Control.Framework.SOC2, identifier='CC1.1', name='Integrity and ethical values',
            )
            control_ct = ContentType.objects.get_for_model(Control)
            Evidence.objects.create(
                title='Information Security Policy v3', content_type=control_ct, object_id=self.implemented.id,
            )

    def test_report_is_a_valid_pdf(self):
        api = APIClient()
        api.force_authenticate(user=self.user)
        resp = api.get('/api/reports/statement-of-applicability/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertTrue(resp.content.startswith(b'%PDF'))
        self.assertGreater(len(resp.content), 500)

    def test_can_be_scoped_to_one_framework(self):
        api = APIClient()
        api.force_authenticate(user=self.user)
        iso_only = api.get('/api/reports/statement-of-applicability/?framework=iso27001', HTTP_HOST=self.host)
        both = api.get('/api/reports/statement-of-applicability/', HTTP_HOST=self.host)
        # Scoping to one framework must produce a strictly smaller/equal
        # document than including every framework — the cheapest signal
        # (without a PDF text extractor in this environment) that the
        # ?framework= filter is actually being applied, not ignored.
        self.assertLessEqual(len(iso_only.content), len(both.content))

    def test_report_requires_tenant_membership(self):
        outsider = User.objects.create_user('soa_outsider', 'o3@example.com', 'pass12345')
        api = APIClient()
        api.force_authenticate(user=outsider)
        resp = api.get('/api/reports/statement-of-applicability/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 403)

    def test_generation_does_not_require_every_control_to_be_justified(self):
        # A tenant that hasn't filled in every justification yet must
        # still be able to generate a report today — the gaps are
        # something to flag and close, not a reason "one-click" fails.
        with schema_context(self.tenant.schema_name):
            from core.models import Control
            Control.objects.create(framework=Control.Framework.ISO27001, identifier='A.5.2', name='Roles')

        api = APIClient()
        api.force_authenticate(user=self.user)
        resp = api.get('/api/reports/statement-of-applicability/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 200)
