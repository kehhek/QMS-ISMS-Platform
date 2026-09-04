"""Proves the primary tenant-isolation mechanism actually holds: every
tenant's QMS/ISMS data lives in a completely separate Postgres schema,
not just separate rows in a shared table. Row-Level Security (see
tenants/migrations/0004_add_rls_to_membership.py) is defense-in-depth on
top of this for the few genuinely shared tables — it isn't what's
protecting Document/Risk/Audit/etc."""

from django.db import connection
from django.test import TestCase
from django_tenants.utils import schema_context

from tenants.models import Client, Domain


def make_tenant(schema_name):
    connection.set_schema_to_public()
    client = Client.objects.create(schema_name=schema_name, name=schema_name)
    Domain.objects.create(domain=f'{schema_name}.localhost', tenant=client, is_primary=True)
    return client


class SchemaIsolationTests(TestCase):
    def test_documents_with_identical_pk_are_not_visible_across_tenants(self):
        tenant_a = make_tenant('isotesta')
        tenant_b = make_tenant('isotestb')

        with schema_context(tenant_a.schema_name):
            from core.models import Document
            doc_a = Document.objects.create(title='Tenant A Only', content='secret A')
            self.assertEqual(doc_a.pk, 1)  # first row in this schema's own sequence

        with schema_context(tenant_b.schema_name):
            from core.models import Document
            # Same PK as tenant A's row, in a schema that has never seen it.
            doc_b = Document.objects.create(title='Tenant B Only', content='secret B')
            self.assertEqual(doc_b.pk, 1)

            # Tenant B's connection can only ever see tenant B's row at pk=1 —
            # there is no query that leaks tenant A's row into this schema,
            # because the table itself (core_document) doesn't exist here;
            # it's a physically different table in tenant A's schema.
            all_titles = list(Document.objects.values_list('title', flat=True))
            self.assertEqual(all_titles, ['Tenant B Only'])

        with schema_context(tenant_a.schema_name):
            from core.models import Document
            all_titles = list(Document.objects.values_list('title', flat=True))
            self.assertEqual(all_titles, ['Tenant A Only'])

    def test_raw_sql_against_current_schema_cannot_see_other_tenants(self):
        tenant_a = make_tenant('isotestc')
        tenant_b = make_tenant('isotestd')

        with schema_context(tenant_a.schema_name):
            from core.models import Risk
            Risk.objects.create(name='Only in A')

        with schema_context(tenant_b.schema_name):
            with connection.cursor() as cursor:
                cursor.execute('SELECT name FROM core_risk')
                rows = [r[0] for r in cursor.fetchall()]
        self.assertEqual(rows, [])
