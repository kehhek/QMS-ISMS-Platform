from django.test import TestCase
from tenants.models import Client, Domain
from django_tenants.utils import schema_context, get_tenant_model
from django.contrib.auth import get_user_model


class TenantModelTests(TestCase):
    def test_create_tenant_and_superuser(self):
        client = Client.objects.create(schema_name='testtenant', name='Test Tenant')
        Domain.objects.create(domain='testtenant.localhost', tenant=client, is_primary=True)

        # inside tenant schema create a user
        with schema_context(client.schema_name):
            User = get_user_model()
            user = User.objects.create_user('user1', 'u1@example.com', 'pass')
            self.assertEqual(User.objects.count(), 1)

    def test_core_models(self):
        # ensure core models are importable in tenant schema
        client = Client.objects.create(schema_name='t2', name='Tenant2')
        Domain.objects.create(domain='t2.localhost', tenant=client, is_primary=True)
        with schema_context(client.schema_name):
            from core.models import Document, Risk
            d = Document.objects.create(title='Doc1')
            r = Risk.objects.create(name='Risk1')
            self.assertEqual(Document.objects.count(), 1)
            self.assertEqual(Risk.objects.count(), 1)
