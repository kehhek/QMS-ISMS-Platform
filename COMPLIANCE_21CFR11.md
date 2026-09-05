# 21 CFR Part 11 — technical controls and gaps

**"Compliant" is a status your organization earns, not one software can
self-certify.** Part 11 requires things no codebase can provide on its
own: a validated-system protocol (IQ/OQ/PQ), SOPs, staff training
records, and — per §11.100(c) — a letter your organization signs and
files with the FDA certifying that your electronic signatures are the
legally binding equivalent of handwritten ones. This document maps each
Part 11 requirement to the technical control implemented here (with file
references) or flags it as your organization's remaining responsibility.
Use it as the input to your own validation package, not as a substitute
for one.

## Subpart B — Electronic Records

| § | Requirement | Status |
|---|---|---|
| 11.10(a) | System validation (accuracy, reliability, consistent performance) | **Your responsibility.** This repo's test suite (`tests/`, 46 tests) is evidence you can build a validation protocol from, but IQ/OQ/PQ execution and sign-off is an organizational process. |
| 11.10(b) | Ability to generate accurate, complete copies of records | `tenants/management/commands/backup_tenants.py` (per-tenant `pg_dump`) + `restore_tenant_test.py` (verifies a backup actually restores, not just that it was taken) |
| 11.10(c) | Protection of records for ready retrieval throughout the retention period | Daily automated backups (Celery Beat, `tenants/tasks.py`), retention count configurable via `BACKUP_RETENTION_COUNT`. **Gap**: no per-record-type retention *schedule* (e.g. "keep audit records 7 years") — that's a records-management policy decision for your organization to configure and enforce. |
| 11.10(d) | Limiting system access to authorized individuals | Token/session auth + per-tenant `Membership` roles (`tenants/permissions.py`) + row-level security on the shared membership table (`tenants/migrations/0004_add_rls_to_membership.py`) |
| 11.10(e) | Secure, computer-generated, time-stamped audit trail of operator entries and actions, independent of the operator, retained at least as long as the records | `core.models.AuditLog` — append-only, enforced at both the ORM layer and a Postgres trigger (`core/migrations/0006_...`) that rejects `UPDATE`/`DELETE` even via raw SQL. Covers create/update/delete on every QMS/ISMS record, logins (success/failure), and now electronic signatures. |
| 11.10(f) | Operational system checks enforcing permitted sequencing | `WorkflowStepViewSet.decide()` (`core/views.py`) rejects deciding a step out of order |
| 11.10(g) | Authority checks — only authorized individuals can use the system, sign, alter a record, etc. | `HasTenantRole` / `HasTenantRoleStrict` (`tenants/permissions.py`) gate every write by tenant role; `decide()` separately checks the specific approver/role required for that step |
| 11.10(h) | Device checks for validity of data source | **Not applicable** in the sense Part 11 means it (this isn't a system with external device/instrument inputs) |
| 11.10(i) | Personnel have appropriate education/training/experience | **Your responsibility.** Not something software can attest to. |
| 11.10(j) | Written policies holding individuals accountable for actions under their electronic signatures | **Your responsibility** — a policy document your organization adopts, referencing the technical signature control below |
| 11.10(k) | Controls over systems documentation, including revision/change control | This repo's own git history + `SECURITY.md`. **Your responsibility** to extend to your SOPs and validation docs specifically. |
| 11.30 | Open-systems controls (encryption, digital signature standards) | TLS is expected in front of this app (`SECURE_SSL_REDIRECT`, HSTS — `project/settings.py`, only outside `DEBUG`); Evidence files are encrypted at rest (`core/storage.py`, Fernet) |
| 11.50 | Signature manifestation: printed name, date/time, meaning | `core.models.ElectronicSignature` — `printed_name` (snapshotted at signing, not a live FK lookup), `meaning` (Approved/Rejected/Reviewed/Authored), `signed_at` |
| 11.70 | Signatures linked to their record so they can't be excised, copied, or transferred to falsify a different record | `ElectronicSignature.integrity_hash` — a SHA-256 over (signer, printed name, meaning, target, timestamp, server secret), checked by `.verify()`; the row itself is immutable (ORM guard + DB trigger, `core/migrations/0012_...`) |

## Subpart C — Electronic Signatures

| § | Requirement | Status |
|---|---|---|
| 11.100(a) | Each signature unique to one individual, never reused/reassigned | Usernames are unique for the life of the row; there's no user-delete feature in this app, only deactivation (`is_active`), so a username is never freed up for reuse. **If you ever add hard user deletion, this constraint must be preserved.** |
| 11.100(b) | Verify identity before establishing/assigning a signature | **Your responsibility** — an identity-verification step in your onboarding process before granting an account, not something the software enforces |
| 11.100(c) | Certification to FDA that electronic signatures are the legally binding equivalent of handwritten ones | **Your responsibility** — a letter your organization files with the FDA. Software cannot do this. |
| 11.200(a)(1) | Non-biometric signatures use ≥2 distinct identification components | `WorkflowStepViewSet.decide()` requires re-entering the password at the moment of signing — a valid token/session (component 1: "who you're logged in as") is deliberately **not** sufficient alone; the password (component 2) is re-verified server-side via `check_password()` before the signature is created |
| 11.200(a)(2)/(3) | Only the genuine owner can use their signature; attempted use by another requires collaboration of ≥2 people | Enforced by the same password re-verification — nobody else can produce it |
| 11.300(a) | Uniqueness of ID/password combinations | Django username uniqueness + `AUTH_PASSWORD_VALIDATORS` (`project/settings.py`: minimum length 10, common-password check, similarity-to-username check, not-entirely-numeric) — previously **unconfigured entirely**, meaning any password (however weak) was accepted before this |
| 11.300(b) | Periodic password revision | `accounts.User.password_changed_at`, `password_expired(max_age_days)`; `PART11_PASSWORD_MAX_AGE_DAYS` (default 90). **Partial**: the age is tracked and queryable, but there's no forced-change UI flow yet that blocks login once expired — that's the remaining piece if you need hard enforcement rather than an auditable flag. |
| 11.300(c) | Loss-management procedures for compromised tokens/cards | **Not applicable** in the token/card sense (no physical tokens); for a compromised password, an admin can invite/reset via `/api/tenant/members/` |
| 11.300(d) | Transaction safeguards against unauthorized use; detect and report attempts | Account lockout after `PART11_MAX_FAILED_LOGINS` (default 5) failed attempts, for `PART11_LOCKOUT_MINUTES` (default 15) — `accounts/security.py`, enforced in both the token and session login views. Every failed attempt (including ones against a locked account) is written to `AuditLog` (`LOGIN_FAILED`), and a failed signature attempt is logged separately (`SIGNATURE_FAILED`). "Report" beyond the audit trail (e.g. alerting) is **your responsibility** to wire up (a Celery task watching for `SIGNATURE_FAILED`/`LOGIN_FAILED` spikes would be a natural extension). |
| 11.300(e) | Periodic testing of ID/password-bearing devices | **Not applicable** (no physical devices) |

## What to do with this document

1. Have your QA/Regulatory Affairs function review the "your responsibility" rows and build them into your actual SOPs and training program.
2. Use the test suite (`tests/test_part11.py` especially) as a starting point for your IQ/OQ validation scripts — it already exercises the signature, lockout, and password-policy behavior directly.
3. Extend `ElectronicSignature` to other record types if your process requires signing more than workflow approvals (e.g. a dedicated "reviewed" signature on a Document independent of the approval workflow) — the model and `core/signatures.py` helper are already generic (a `GenericForeignKey`), so this is a new call site, not new infrastructure.
4. If you need hard password-expiry enforcement (not just the tracked flag), add a check in the authentication path that blocks login and forces a password change once `password_expired()` is true.
