import secrets
import string

from django.core.management.base import BaseCommand
from tenants.models import Client, Domain
from django_tenants.utils import schema_context
from django.contrib.auth import get_user_model


def generate_password(length=20):
    alphabet = string.ascii_letters + string.digits + '!@#%^&*-_+='
    return ''.join(secrets.choice(alphabet) for _ in range(length))


class Command(BaseCommand):
    help = 'Create a tenant schema, domain, and a superuser inside that tenant'

    def add_arguments(self, parser):
        parser.add_argument('--name', required=True, help='Tenant name')
        parser.add_argument('--schema', required=True, help='Schema name for tenant')
        parser.add_argument('--domain', required=True, help='Domain (eg: tenant.localhost)')
        parser.add_argument('--username', default='admin', help='Superuser username')
        parser.add_argument('--email', default='admin@example.com', help='Superuser email')
        parser.add_argument(
            '--password',
            default=None,
            help='Superuser password. If omitted, a strong random password is generated and printed.',
        )

    def handle(self, *args, **options):
        name = options['name']
        schema = options['schema']
        domain = options['domain']
        username = options['username']
        email = options['email']
        password = options['password'] or generate_password()
        password_was_generated = options['password'] is None

        client = Client(schema_name=schema, name=name)
        client.save()
        Domain.objects.create(domain=domain, tenant=client, is_primary=True)

        self.stdout.write(self.style.SUCCESS(f'Created tenant {name} (schema={schema})'))

        # create superuser inside tenant schema
        with schema_context(client.schema_name):
            User = get_user_model()
            if not User.objects.filter(username=username).exists():
                User.objects.create_superuser(username=username, email=email, password=password)
                self.stdout.write(self.style.SUCCESS(f'Created superuser {username} in schema {schema}'))
                if password_was_generated:
                    self.stdout.write(self.style.WARNING(f'Generated password: {password}'))
            else:
                self.stdout.write(self.style.WARNING('Superuser already exists in tenant schema'))
