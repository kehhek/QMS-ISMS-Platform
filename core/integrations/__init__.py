"""Continuous, automated control evidence — the actual differentiator
this package exists for: instead of an admin manually flipping a
Control to "Implemented" once and it silently going stale, a connected
Integration (see core.models.Integration) is synced against the real
third-party system and the matching Control + a fresh, dated Evidence
row are updated to match reality every time.

- base.py: the CheckOutcome shape every provider returns, and
  IntegrationError for a sync that couldn't complete.
- github.py / aws.py: one provider each. Both talk to the real API
  (urllib for GitHub, boto3 — already a dependency for S3 evidence
  storage — for AWS) with no other new third-party dependency.
- registry.py: provider key -> instance, looked up by Integration.provider.
- sync.py: the actual "run this integration's checks and update
  Controls/Evidence/IntegrationCheckResult" logic, shared by every
  provider so that part only exists once.

Adding a new provider (Okta, Google Workspace, GCP, ...) is: one new
file implementing `test_connection(credentials, config)` and
`run_checks(credentials, config) -> list[CheckOutcome]`, one line in
registry.py, and one new Integration.Provider choice.
"""
