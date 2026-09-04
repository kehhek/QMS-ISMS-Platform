import gzip
import os
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


def _latest_backup(schema):
    backup_dir = Path(settings.BACKUP_ROOT) / schema
    candidates = sorted(backup_dir.glob(f'{schema}_*.sql.gz'), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


class Command(BaseCommand):
    help = (
        'Restore a tenant backup into a throwaway database to verify it actually '
        'works, then drop that database. Never touches the real tenant schema — '
        'this is what makes a backup "tested" rather than just "taken".\n\n'
        'A tenant schema backup on its own is not standalone-restorable: its '
        'foreign keys point at shared public-schema tables (accounts_user, '
        'tenants_client, django_content_type, ...) that a --schema=<tenant> dump '
        "never includes. So this also restores the public schema's own backup "
        'first, into the same scratch database, before the tenant schema.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--schema', required=True, help='Original tenant schema the backup is for.')
        parser.add_argument('--file', help='Specific backup file for --schema. Defaults to the most recent.')

    def handle(self, *args, **options):
        schema = options['schema']

        if options['file']:
            tenant_backup_path = Path(options['file'])
        else:
            tenant_backup_path = _latest_backup(schema)
            if tenant_backup_path is None:
                raise CommandError(f'No backups found for schema "{schema}".')
        if not tenant_backup_path.exists():
            raise CommandError(f'Backup file not found: {tenant_backup_path}')

        restore_order = [tenant_backup_path]
        if schema != 'public':
            public_backup_path = _latest_backup('public')
            if public_backup_path is None:
                raise CommandError(
                    'No "public" schema backup found — required to satisfy this tenant '
                    'schema\'s foreign keys (accounts_user, tenants_client, etc). Run '
                    '`backup_tenants` (which always includes public) first.'
                )
            restore_order = [public_backup_path, tenant_backup_path]

        db = settings.DATABASES['default']
        env = os.environ.copy()
        if db.get('PASSWORD'):
            env['PGPASSWORD'] = db['PASSWORD']
        host, port, user = db.get('HOST') or 'localhost', str(db.get('PORT') or '5432'), db.get('USER') or 'postgres'
        scratch_db = f"{db['NAME']}_restoretest"

        def run(cmd, **kwargs):
            return subprocess.run(cmd, env=env, capture_output=True, **kwargs)

        self.stdout.write(
            f'Restore-testing {[p.name for p in restore_order]} into throwaway database "{scratch_db}" ...'
        )

        run(['dropdb', '-h', host, '-p', port, '-U', user, '--if-exists', scratch_db])
        result = run(['createdb', '-h', host, '-p', port, '-U', user, scratch_db])
        if result.returncode != 0:
            raise CommandError(f'Could not create scratch database: {result.stderr.decode()[:500]}')

        # A freshly created database already has a default "public" schema,
        # which collides with the dump's own `CREATE SCHEMA public;` — drop
        # it first so the restore starts from a truly empty database.
        result = run([
            'psql', '-h', host, '-p', port, '-U', user, '-d', scratch_db,
            '-c', 'DROP SCHEMA public CASCADE',
        ])
        if result.returncode != 0:
            raise CommandError(f'Could not drop the default public schema: {result.stderr.decode()[:500]}')

        try:
            for backup_path in restore_order:
                with gzip.open(backup_path, 'rb') as f:
                    sql = f.read()
                result = run(
                    ['psql', '-h', host, '-p', port, '-U', user, '-d', scratch_db, '-v', 'ON_ERROR_STOP=1'],
                    input=sql,
                )
                if result.returncode != 0:
                    raise CommandError(f'Restoring {backup_path.name} failed: {result.stderr.decode()[:1000]}')

            # A real parameterized query here (not string-interpolated into a
            # psql -c argument) — schema names come from the trusted Client
            # table, not request input, but there's no reason to build a SQL
            # injection pattern regardless.
            import psycopg2

            conn = psycopg2.connect(host=host, port=port, user=user, password=db.get('PASSWORD'), dbname=scratch_db)
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        'SELECT count(*) FROM information_schema.tables WHERE table_schema = %s', [schema],
                    )
                    table_count = cur.fetchone()[0]
            finally:
                conn.close()

            if not table_count:
                raise CommandError(f'Restore produced no tables in schema "{schema}" — backup is likely broken.')

            self.stdout.write(self.style.SUCCESS(
                f'Restore OK: schema "{schema}" restored with {table_count} tables in the scratch database.'
            ))
        finally:
            run(['dropdb', '-h', host, '-p', port, '-U', user, '--if-exists', scratch_db])
            self.stdout.write('Scratch database dropped.')
