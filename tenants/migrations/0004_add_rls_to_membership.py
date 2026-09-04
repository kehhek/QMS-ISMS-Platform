from django.db import migrations

# Defense-in-depth on the one shared table where a permission-check bug
# could leak rows across tenants. See tenants/middleware.py for the caveat:
# this is inert against a superuser DB connection (Postgres never applies
# RLS to superusers), which is what dev uses by default.
ENABLE_RLS_SQL = """
ALTER TABLE tenants_membership ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenants_membership FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_membership_isolation ON tenants_membership
    USING (
        current_setting('app.current_tenant_id', true) IS NULL
        OR current_setting('app.current_tenant_id', true) = ''
        OR tenant_id = current_setting('app.current_tenant_id', true)::integer
    )
    WITH CHECK (
        current_setting('app.current_tenant_id', true) IS NULL
        OR current_setting('app.current_tenant_id', true) = ''
        OR tenant_id = current_setting('app.current_tenant_id', true)::integer
    );
"""

DISABLE_RLS_SQL = """
DROP POLICY IF EXISTS tenant_membership_isolation ON tenants_membership;
ALTER TABLE tenants_membership NO FORCE ROW LEVEL SECURITY;
ALTER TABLE tenants_membership DISABLE ROW LEVEL SECURITY;
"""


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0003_client_logo_url_client_primary_color_and_more'),
    ]

    operations = [
        migrations.RunSQL(sql=ENABLE_RLS_SQL, reverse_sql=DISABLE_RLS_SQL),
    ]
