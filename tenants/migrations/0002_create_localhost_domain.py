from django.db import migrations


def create_localhost_domain(apps, schema_editor):
    Client = apps.get_model('tenants', 'Client')
    Domain = apps.get_model('tenants', 'Domain')
    try:
        public = Client.objects.get(schema_name='public')
    except Client.DoesNotExist:
        return
    Domain.objects.get_or_create(domain='localhost', tenant=public)


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0001_squashed_0001'),
    ]

    operations = [
        migrations.RunPython(create_localhost_domain, migrations.RunPython.noop),
    ]
