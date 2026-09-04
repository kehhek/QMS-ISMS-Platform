from django.db import migrations


def create_localhost_domain(apps, schema_editor):
    Client = apps.get_model('tenants', 'Client')
    Domain = apps.get_model('tenants', 'Domain')
    try:
        public = Client.objects.get(schema_name='public')
    except Client.DoesNotExist:
        return
    # `domain` is unique, so don't try to create a second row if 'localhost'
    # is already registered against a different tenant (e.g. a dev tenant).
    if Domain.objects.filter(domain='localhost').exists():
        return
    Domain.objects.get_or_create(domain='localhost', tenant=public)


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_localhost_domain, migrations.RunPython.noop),
    ]
