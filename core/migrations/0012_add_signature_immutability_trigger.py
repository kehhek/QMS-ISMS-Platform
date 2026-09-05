from django.db import migrations

# Same reasoning as migration 0006 for AuditLog: ElectronicSignature.save()/
# .delete() already reject mutation at the ORM layer, but that's bypassable
# via bulk_update(), raw SQL, or the admin's bulk actions. A Part 11
# electronic signature that could be silently edited or deleted after the
# fact isn't a signature — this makes UPDATE/DELETE fail in Postgres itself,
# regardless of how it's attempted.
CREATE_TRIGGER_SQL = """
CREATE OR REPLACE FUNCTION core_signature_block_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'ElectronicSignature entries are immutable (append-only) and cannot be % on row id=%', TG_OP, OLD.id;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER core_signature_no_update
BEFORE UPDATE ON core_electronicsignature
FOR EACH ROW EXECUTE FUNCTION core_signature_block_mutation();

CREATE TRIGGER core_signature_no_delete
BEFORE DELETE ON core_electronicsignature
FOR EACH ROW EXECUTE FUNCTION core_signature_block_mutation();
"""

DROP_TRIGGER_SQL = """
DROP TRIGGER IF EXISTS core_signature_no_update ON core_electronicsignature;
DROP TRIGGER IF EXISTS core_signature_no_delete ON core_electronicsignature;
DROP FUNCTION IF EXISTS core_signature_block_mutation();
"""


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_alter_auditlog_action_electronicsignature'),
    ]

    operations = [
        migrations.RunSQL(sql=CREATE_TRIGGER_SQL, reverse_sql=DROP_TRIGGER_SQL),
    ]
