# Security

## Tenant data isolation

Primary isolation is **schema-based**: every tenant's QMS/ISMS data (Document,
Risk, Audit, Control, Incident, CorrectiveAction, Evidence, Workflow,
AuditLog, ...) lives in its own Postgres schema, provisioned via
django-tenants. This is stronger than row-level filtering — the tables
themselves are physically separate per tenant, so there's no query that can
accidentally return another tenant's rows from this data. See
`tests/test_tenant_isolation.py`.

A handful of tables are deliberately shared across every tenant in the public
schema (`accounts.User`, `tenants.Client`, `tenants.Domain`,
`tenants.Membership`) — this is what makes one global user able to belong to
multiple tenants. `tenants_membership` (which carries per-tenant *roles*, the
most sensitive shared data) has Postgres Row-Level Security enabled as
defense-in-depth, scoped via a session variable set by
`tenants.middleware.TenantSessionScopeMiddleware`. **Caveat**: Postgres never
enforces RLS against a superuser role, and the default dev `DATABASES` config
connects as `postgres` (a superuser) — so this policy is real, tested, and
currently inert. It only takes effect once the app connects as a
non-superuser role with the right grants; this hasn't been done in the
default dev setup since it changes live DB credentials.

## Encryption

- **In transit**: this app doesn't terminate TLS itself — that's a reverse
  proxy / load balancer's job. `project/settings.py` enables
  `SECURE_SSL_REDIRECT`, HSTS, and secure cookies whenever `DJANGO_DEBUG=False`,
  trusting `X-Forwarded-Proto` from the proxy.
- **At rest**: Evidence file uploads are encrypted with Fernet before they
  touch disk (`core/storage.py`), decrypted transparently on read. The key
  (`EVIDENCE_ENCRYPTION_KEY`) has a fixed dev-only default; production must
  set its own via env and never commit it. This protects file *content*
  only — filenames and directory structure are still visible on disk.
  Database-level encryption at rest (the Postgres data directory itself) is
  an infrastructure decision (encrypted volume/disk), not something this app
  configures.

## Audit logging

`core.models.AuditLog` is append-only: `save()`/`delete()` reject mutating an
existing row at the ORM layer, and a Postgres trigger
(`core_auditlog_block_mutation`, migration `core/migrations/0006_...`)
rejects `UPDATE`/`DELETE` on the table itself — verified to block both
`queryset.update()` and raw SQL, not just the ORM path. Logged today: create/
update/destroy on every QMS/ISMS model, workflow step approve/reject,
successful and failed logins (both token and session), and tenant
settings/membership changes.

## Backups

`python manage.py backup_tenants` dumps every tenant schema (each one
individually, `pg_dump --schema=<name>`) to a gzipped SQL file under
`BACKUP_ROOT` (`./backups/`), pruning beyond `BACKUP_RETENTION_COUNT` (14 by
default). Runs daily at 02:00 via Celery Beat
(`tenants.tasks.run_daily_backups`).

**A single tenant schema's backup is not standalone-restorable** — its
foreign keys point at shared public-schema tables (`accounts_user`,
`tenants_client`, ...) that a `--schema=<tenant>` dump doesn't include.
`backup_tenants` always includes a `public` backup for this reason.

To actually verify a backup restores (not just that it was taken):
```
python manage.py restore_tenant_test --schema <name>
```
This restores the `public` backup and then the named tenant's backup into a
throwaway database (`<db>_restoretest`), checks it produced real tables, and
drops the throwaway database. It never touches the real database. Run this
periodically, not just when a backup is taken — the point is to catch a
backup that silently stopped being restorable.

## Dependency & static-analysis scanning

Every CI run (`.github/workflows/ci.yml`, `security` job):
- `pip-audit` against `requirements.txt` (report-only right now — see below)
- `bandit` static analysis on the Python source (blocking at medium+ severity)
- `npm audit` on the frontend (report-only — existing `react-scripts`
  transitive deps carry known issues not cheap to fix without a bigger
  tooling migration)

**Known, currently unaddressed**: `pip-audit` flags 7 CVEs against
Django 4.2.30. The fixes are on 5.2.x/6.0.x, both outside this project's
`Django>=4.2,<5` pin — that's a deliberate major-version upgrade decision
(compatibility with django-tenants and everything else needs checking first),
not something to do silently as a side effect of adding a scanner. Tracked
here rather than hidden by making the check non-blocking without a note.

## Penetration testing

This is a scheduled, human-led process, not something CI or an AI coding
assistant substitutes for. For any deployment handling real tenant data,
budget for a third-party pentest before the first production launch and at
least annually (or before any major architecture change) after that. An
automated code-level security review (e.g. this repo's `/security-review` or
`/code-review` tooling) can catch some classes of bugs between pentests, but
it is a complement, not a replacement.
