from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Run initial migrations and bootstrap a sample tenant for development'

    def handle(self, *args, **options):
        self.stdout.write('Running initial migrations...')
        call_command('migrate', verbosity=1, interactive=False)

        self.stdout.write('Creating a sample tenant using bootstrap_tenant...')
        try:
            call_command('bootstrap_tenant', name='SampleTenant', schema='sample', domain='sample.localhost', username='admin', email='admin@example.com')
            self.stdout.write(self.style.SUCCESS('Sample tenant created.'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Could not create tenant automatically: {e}'))
            self.stdout.write('You can create a tenant manually with `python manage.py bootstrap_tenant --name ...`')

        self.stdout.write(self.style.SUCCESS('Init complete.'))
