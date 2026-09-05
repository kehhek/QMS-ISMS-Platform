from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context, get_tenant_model

from core.data.control_catalogs import ISO27001_CONTROLS, SOC2_CONTROLS


class Command(BaseCommand):
    help = (
        'Load the full ISO/IEC 27001:2022 Annex A catalog (93 controls) and the '
        'SOC 2 Common Criteria (33 controls, CC1-CC9) into one or more tenant '
        'schemas. Safe to re-run — existing controls (matched by framework + '
        'identifier) are left untouched, not duplicated or overwritten.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--schema', action='append', dest='schemas',
            help='Tenant schema to load into. Repeatable. Defaults to every non-public tenant.',
        )

    def handle(self, *args, **options):
        Client = get_tenant_model()
        schemas = options['schemas']
        if not schemas:
            schemas = list(
                Client.objects.exclude(schema_name='public').values_list('schema_name', flat=True)
            )

        if not schemas:
            self.stdout.write(self.style.WARNING('No tenant schemas found.'))
            return

        for schema in schemas:
            self.load_catalog(schema)

    def load_catalog(self, schema):
        from core.models import Control

        with schema_context(schema):
            iso_added = 0
            for identifier, name in ISO27001_CONTROLS:
                _, created = Control.objects.get_or_create(
                    framework=Control.Framework.ISO27001, identifier=identifier,
                    defaults={'name': name},
                )
                iso_added += int(created)

            soc2_added = 0
            for identifier, name in SOC2_CONTROLS:
                _, created = Control.objects.get_or_create(
                    framework=Control.Framework.SOC2, identifier=identifier,
                    defaults={'name': name},
                )
                soc2_added += int(created)

            iso_total = Control.objects.filter(framework=Control.Framework.ISO27001).count()
            soc2_total = Control.objects.filter(framework=Control.Framework.SOC2).count()
            self.stdout.write(self.style.SUCCESS(
                f'Schema "{schema}": +{iso_added} ISO 27001 controls (now {iso_total}), '
                f'+{soc2_added} SOC 2 controls (now {soc2_total}).'
            ))
