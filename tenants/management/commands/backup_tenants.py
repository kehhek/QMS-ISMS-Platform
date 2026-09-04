import datetime
import gzip
import os
import re
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django_tenants.utils import get_tenant_model

# pg_dump's client version can be newer than the Postgres server it's
# dumping (the base image's package repo only carries the latest major
# version; the server here is pinned to postgres:15 in docker-compose).
# A newer pg_dump emits preamble SET statements for GUCs that don't exist
# on an older server — e.g. PG17's client added `SET transaction_timeout`,
# which PG15 rejects outright on restore. Strip anything on this narrow,
# specific list so the backup we actually write is the one we can actually
# restore, rather than finding out at restore time (or disaster time).
INCOMPATIBLE_PREAMBLE_PATTERNS = [
    re.compile(rb'^SET transaction_timeout\s*=.*;\s*$', re.MULTILINE),
]


def _strip_incompatible_preamble(dump_bytes):
    for pattern in INCOMPATIBLE_PREAMBLE_PATTERNS:
        dump_bytes = pattern.sub(b'', dump_bytes)
    return dump_bytes


class Command(BaseCommand):
    help = 'Back up each tenant schema (or specific ones via --schema) as a gzipped SQL dump.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--schema', action='append', dest='schemas',
            help='Schema to back up. Repeatable. Defaults to every tenant.',
        )

    def handle(self, *args, **options):
        Client = get_tenant_model()
        schemas = options['schemas'] or list(Client.objects.values_list('schema_name', flat=True))

        db = settings.DATABASES['default']
        env = os.environ.copy()
        if db.get('PASSWORD'):
            env['PGPASSWORD'] = db['PASSWORD']
        host, port, user = db.get('HOST') or 'localhost', str(db.get('PORT') or '5432'), db.get('USER') or 'postgres'

        timestamp = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')

        for schema in schemas:
            out_dir = Path(settings.BACKUP_ROOT) / schema
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f'{schema}_{timestamp}.sql.gz'

            cmd = [
                'pg_dump', '-h', host, '-p', port, '-U', user, '-d', db['NAME'],
                '--schema', schema, '--no-owner', '--no-privileges', '--format=plain',
            ]
            result = subprocess.run(cmd, env=env, capture_output=True)
            if result.returncode != 0:
                self.stderr.write(self.style.ERROR(
                    f'Backup failed for schema "{schema}": {result.stderr.decode()[:500]}'
                ))
                continue

            with gzip.open(out_path, 'wb') as f:
                f.write(_strip_incompatible_preamble(result.stdout))

            size_kb = out_path.stat().st_size / 1024
            self.stdout.write(self.style.SUCCESS(f'Backed up "{schema}" -> {out_path} ({size_kb:.1f} KB)'))
            self._prune_old_backups(out_dir, schema)

    def _prune_old_backups(self, out_dir, schema):
        retention = getattr(settings, 'BACKUP_RETENTION_COUNT', 14)
        backups = sorted(out_dir.glob(f'{schema}_*.sql.gz'), key=lambda p: p.stat().st_mtime, reverse=True)
        for stale in backups[retention:]:
            stale.unlink()
            self.stdout.write(f'Pruned old backup: {stale.name}')
