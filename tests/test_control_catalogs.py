from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django_tenants.utils import schema_context
from rest_framework.test import APIClient

from core.data.control_catalogs import CATALOGS_BY_FRAMEWORK, ISO27001_CONTROLS, SOC2_CONTROLS
from tenants.models import Client, Domain, Membership

User = get_user_model()


def make_tenant(schema_name):
    connection.set_schema_to_public()
    client = Client.objects.create(schema_name=schema_name, name=schema_name)
    Domain.objects.create(domain=f'{schema_name}.localhost', tenant=client, is_primary=True)
    return client


def make_member(tenant, username, role, password='pass12345'):
    user = User.objects.create_user(username, f'{username}@example.com', password)
    Membership.objects.create(user=user, tenant=tenant, role=role)
    return user


class ControlCatalogDataTests(TestCase):
    def test_catalog_sizes_and_uniqueness(self):
        self.assertEqual(len(ISO27001_CONTROLS), 93)
        self.assertEqual(len(SOC2_CONTROLS), 33)

        iso_ids = [identifier for identifier, _ in ISO27001_CONTROLS]
        soc2_ids = [identifier for identifier, _ in SOC2_CONTROLS]
        self.assertEqual(len(iso_ids), len(set(iso_ids)))
        self.assertEqual(len(soc2_ids), len(set(soc2_ids)))

    def test_every_additional_catalog_has_unique_identifiers(self):
        for framework, catalog in CATALOGS_BY_FRAMEWORK.items():
            with self.subTest(framework=framework):
                ids = [identifier for identifier, _ in catalog]
                self.assertEqual(len(ids), len(set(ids)), f'{framework} has duplicate identifiers')


class ControlMappingDataTests(TestCase):
    """The cross-framework mapping data (core/data/control_mappings.py)
    is only useful if every identifier it references actually exists in
    the catalogs — a typo here would silently mean "no mapping found"
    rather than a loud failure, so this is worth its own test."""

    def test_every_mapped_control_exists_in_its_catalog(self):
        from core.data.control_mappings import CONTROL_MAPPING_GROUPS

        catalog_ids = {
            (framework, identifier)
            for framework, catalog in CATALOGS_BY_FRAMEWORK.items()
            for identifier, _name in catalog
        }
        for group in CONTROL_MAPPING_GROUPS:
            for framework, identifier in group['controls']:
                with self.subTest(theme=group['theme'], framework=framework, identifier=identifier):
                    self.assertIn((framework, identifier), catalog_ids)

    def test_every_group_has_at_least_two_controls(self):
        from core.data.control_mappings import CONTROL_MAPPING_GROUPS

        for group in CONTROL_MAPPING_GROUPS:
            with self.subTest(theme=group['theme']):
                self.assertGreaterEqual(len(group['controls']), 2)

    def test_equivalents_index_is_symmetric(self):
        from core.data.control_mappings import EQUIVALENTS_INDEX

        for key, equivalents in EQUIVALENTS_INDEX.items():
            for other_framework, other_identifier, _theme in equivalents:
                with self.subTest(key=key, other=(other_framework, other_identifier)):
                    back_refs = {(f, i) for f, i, _t in EQUIVALENTS_INDEX[(other_framework, other_identifier)]}
                    self.assertIn(key, back_refs)


class CrossFrameworkCoverageApiTests(TestCase):
    """ControlViewSet.seed_framework / framework_coverage / mappings —
    the actual "you're already N% covered" product surface."""

    def setUp(self):
        self.tenant = make_tenant('xframeapitest')
        self.host = f'{self.tenant.schema_name}.localhost'
        self.admin = make_member(self.tenant, 'xf_admin', Membership.Role.ADMIN)
        self.plain_user = make_member(self.tenant, 'xf_user', Membership.Role.USER)
        with schema_context(self.tenant.schema_name):
            from core.models import Control
            self.access_control = Control.objects.create(
                framework='iso27001', identifier='A.5.15', name='Access control', status='implemented',
            )

        self.api = APIClient()
        self.api.force_authenticate(user=self.admin)

    def test_plain_user_can_preview_coverage(self):
        api = APIClient()
        api.force_authenticate(user=self.plain_user)
        resp = api.get('/api/controls/framework-coverage/?framework=nist_csf', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 200)

    def test_coverage_reflects_an_implemented_mapped_control(self):
        resp = self.api.get('/api/controls/framework-coverage/?framework=nist_csf', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data['already_covered_count'], 1)
        praa = next(c for c in resp.data['controls'] if c['identifier'] == 'PR.AA')
        self.assertTrue(praa['already_covered'])
        self.assertEqual(praa['covering_controls'][0]['identifier'], 'A.5.15')

    def test_coverage_ignores_a_mapped_control_that_isnt_implemented_yet(self):
        with schema_context(self.tenant.schema_name):
            self.access_control.status = 'not_implemented'
            self.access_control.save()

        resp = self.api.get('/api/controls/framework-coverage/?framework=nist_csf', HTTP_HOST=self.host)
        self.assertEqual(resp.data['already_covered_count'], 0)

    def test_unknown_framework_is_a_clean_400(self):
        resp = self.api.get('/api/controls/framework-coverage/?framework=made-up', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 400)

    def test_plain_user_cannot_seed_a_framework(self):
        api = APIClient()
        api.force_authenticate(user=self.plain_user)
        resp = api.post(
            '/api/controls/seed-framework/', {'framework': 'hipaa'}, format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_seed_a_framework_and_it_is_idempotent(self):
        first = self.api.post(
            '/api/controls/seed-framework/', {'framework': 'hipaa'}, format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(first.data['added_count'], 21)

        second = self.api.post(
            '/api/controls/seed-framework/', {'framework': 'hipaa'}, format='json', HTTP_HOST=self.host,
        )
        self.assertEqual(second.data['added_count'], 0)
        self.assertEqual(second.data['total_count'], 21)

    def test_mappings_action_shows_seeded_and_unseeded_equivalents(self):
        resp = self.api.get(f'/api/controls/{self.access_control.id}/mappings/', HTTP_HOST=self.host)
        self.assertEqual(resp.status_code, 200, resp.data)
        by_id = {(m['framework'], m['identifier']): m for m in resp.data}
        # soc2 CC6.1 isn't seeded in this tenant at all.
        self.assertFalse(by_id[('soc2', 'CC6.1')]['seeded'])
        self.assertIsNone(by_id[('soc2', 'CC6.1')]['control_id'])

    def test_mappings_reflects_a_seeded_equivalents_real_status(self):
        with schema_context(self.tenant.schema_name):
            from core.models import Control
            soc2_control = Control.objects.create(framework='soc2', identifier='CC6.1', name='Access', status='partial')

        resp = self.api.get(f'/api/controls/{self.access_control.id}/mappings/', HTTP_HOST=self.host)
        by_id = {(m['framework'], m['identifier']): m for m in resp.data}
        self.assertTrue(by_id[('soc2', 'CC6.1')]['seeded'])
        self.assertEqual(by_id[('soc2', 'CC6.1')]['control_id'], soc2_control.id)
        self.assertEqual(by_id[('soc2', 'CC6.1')]['status'], 'partial')


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
