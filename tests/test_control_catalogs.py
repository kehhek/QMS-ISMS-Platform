from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django_tenants.utils import schema_context

from core.data.control_catalogs import ISO27001_CONTROLS, SOC2_CONTROLS
from tenants.models import Client, Domain


def make_tenant(schema_name):
    connection.set_schema_to_public()
    client = Client.objects.create(schema_name=schema_name, name=schema_name)
    Domain.objects.create(domain=f'{schema_name}.localhost', tenant=client, is_primary=True)
    return client


class ControlCatalogDataTests(TestCase):
    def test_catalog_sizes_and_uniqueness(self):
        self.assertEqual(len(ISO27001_CONTROLS), 93)
        self.assertEqual(len(SOC2_CONTROLS), 33)

        iso_ids = [identifier for identifier, _ in ISO27001_CONTROLS]
        soc2_ids = [identifier for identifier, _ in SOC2_CONTROLS]
        self.assertEqual(len(iso_ids), len(set(iso_ids)))
        self.assertEqual(len(soc2_ids), len(set(soc2_ids)))


class SeedControlCatalogsCommandTests(TestCase):
    def test_seeding_loads_all_controls_and_is_idempotent(self):
        tenant = make_tenant('catalogtest')

        call_command('seed_control_catalogs', schema=[tenant.schema_name])

        with schema_context(tenant.schema_name):
            from core.models import Control

            self.assertEqual(Control.objects.filter(framework=Control.Framework.ISO27001).count(), 93)
            self.assertEqual(Control.objects.filter(framework=Control.Framework.SOC2).count(), 33)
            self.assertEqual(Control.objects.count(), 126)

            # Sanity-check a couple of specific, well-known identifiers.
            self.assertTrue(Control.objects.filter(
                framework=Control.Framework.ISO27001, identifier='A.5.1', name='Policies for information security',
            ).exists())
            self.assertTrue(Control.objects.filter(
                framework=Control.Framework.SOC2, identifier='CC6.1',
            ).exists())

        # Re-running must not create duplicates.
        call_command('seed_control_catalogs', schema=[tenant.schema_name])
        with schema_context(tenant.schema_name):
            from core.models import Control
            self.assertEqual(Control.objects.count(), 126)
