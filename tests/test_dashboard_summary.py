from django.db import connection
from django.test import TestCase
from rest_framework.test import APIClient

from tenants.models import Client, Domain, Membership
from django.contrib.auth import get_user_model

User = get_user_model()


def make_tenant(schema_name):
    connection.set_schema_to_public()
    client = Client.objects.create(schema_name=schema_name, name=schema_name)
    Domain.objects.create(domain=f'{schema_name}.localhost', tenant=client, is_primary=True)
    return client


class DashboardSummaryTests(TestCase):
    def test_summary_aggregates_correctly_by_status_and_framework(self):
        tenant = make_tenant('dashboardtest')
        user = User.objects.create_user('dash_user', 'd@example.com', 'pass12345')
        Membership.objects.create(user=user, tenant=tenant, role=Membership.Role.USER)

        from django_tenants.utils import schema_context
        with schema_context(tenant.schema_name):
            from core.models import Document, Control, Incident

            Document.objects.create(title='A', status=Document.Status.DRAFT)
            Document.objects.create(title='B', status=Document.Status.APPROVED)
            Document.objects.create(title='C', status=Document.Status.APPROVED)

            Control.objects.create(framework=Control.Framework.ISO27001, identifier='A.1', name='x', status=Control.Status.IMPLEMENTED)
            Control.objects.create(framework=Control.Framework.ISO27001, identifier='A.2', name='y', status=Control.Status.NOT_IMPLEMENTED)
            Control.objects.create(framework=Control.Framework.SOC2, identifier='CC1.1', name='z', status=Control.Status.PARTIAL)

            Incident.objects.create(title='I1', severity=Incident.Severity.HIGH, status=Incident.Status.OPEN)
            Incident.objects.create(title='I2', severity=Incident.Severity.LOW, status=Incident.Status.CLOSED)

        api = APIClient()
        api.force_authenticate(user=user)
        response = api.get('/api/dashboard-summary/', HTTP_HOST=f'{tenant.schema_name}.localhost')

        self.assertEqual(response.status_code, 200)
        data = response.data

        self.assertEqual(data['documents'], {'draft': 1, 'approved': 2})
        self.assertEqual(data['totals']['documents'], 3)
        self.assertEqual(data['controls']['iso27001'], {'implemented': 1, 'not_implemented': 1})
        self.assertEqual(data['controls']['soc2'], {'partial': 1})
        self.assertEqual(data['totals']['controls'], 3)
        self.assertEqual(data['incidents'], {'high': 1, 'low': 1})
        # Regression test: 'incidents' is keyed by severity, not status —
        # a closed incident must show up as closed in the STATUS
        # breakdown so the dashboard's "open incidents" count can
        # actually exclude it (see DashboardPanel.js's openIncidents,
        # which used to read .resolved/.closed off this severity-keyed
        # object and always get undefined, i.e. never actually excluding
        # anything).
        self.assertEqual(data['incidents_by_status'], {'open': 1, 'closed': 1})
        self.assertEqual(data['totals']['incidents'], 2)
