from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from rest_framework.test import APIClient

from tenants.models import Client, Domain, Membership

User = get_user_model()


def make_tenant(schema_name):
    connection.set_schema_to_public()
    client = Client.objects.create(schema_name=schema_name, name=schema_name)
    Domain.objects.create(domain=f'{schema_name}.localhost', tenant=client, is_primary=True)
    return client


class SupplierCrudTests(TestCase):
    def test_full_create_update_delete_cycle(self):
        tenant = make_tenant('suppliertest')
        user = User.objects.create_user('supplier_admin', 's@example.com', 'pass12345')
        Membership.objects.create(user=user, tenant=tenant, role=Membership.Role.ADMIN)

        api = APIClient()
        api.force_authenticate(user=user)
        host = f'{tenant.schema_name}.localhost'

        create = api.post('/api/suppliers/', {
            'name': 'Acme Hosting', 'contact_email': 'ops@acmehosting.example.com', 'status': 'under_review',
        }, HTTP_HOST=host)
        self.assertEqual(create.status_code, 201, create.data)
        supplier_id = create.data['id']

        update = api.patch(f'/api/suppliers/{supplier_id}/', {'status': 'active'}, HTTP_HOST=host)
        self.assertEqual(update.status_code, 200)
        self.assertEqual(update.data['status'], 'active')

        listing = api.get('/api/suppliers/', HTTP_HOST=host)
        self.assertEqual(listing.data['count'], 1)

        delete = api.delete(f'/api/suppliers/{supplier_id}/', HTTP_HOST=host)
        self.assertEqual(delete.status_code, 204)

        listing_after = api.get('/api/suppliers/', HTTP_HOST=host)
        self.assertEqual(listing_after.data['count'], 0)

        # Every write is audit-logged too.
        from django_tenants.utils import schema_context
        with schema_context(tenant.schema_name):
            from core.models import AuditLog
            actions = set(AuditLog.objects.values_list('action', flat=True))
            self.assertIn('create', actions)
            self.assertIn('update', actions)
            self.assertIn('delete', actions)

    def test_auditor_role_cannot_write_suppliers(self):
        tenant = make_tenant('suppliertestauditor')
        user = User.objects.create_user('supplier_auditor', 'a@example.com', 'pass12345')
        Membership.objects.create(user=user, tenant=tenant, role=Membership.Role.AUDITOR)

        api = APIClient()
        api.force_authenticate(user=user)
        response = api.post(
            '/api/suppliers/', {'name': 'Should Fail'}, HTTP_HOST=f'{tenant.schema_name}.localhost',
        )
        self.assertEqual(response.status_code, 403)
