from dataclasses import dataclass


@dataclass
class CheckOutcome:
    """One provider check's result for one sync run. `control_identifier`
    + `control_framework` name a real, already-seeded Control (see
    core/data/control_catalogs.py) this check is evidence for — sync.py
    looks that Control up and updates it; if it doesn't exist in this
    tenant's catalog (e.g. a custom framework), the check result is still
    recorded, just with no Control attached."""

    key: str
    label: str
    passed: bool
    detail: str
    control_identifier: str
    control_framework: str = 'iso27001'


class IntegrationError(Exception):
    """Raised by a provider when a sync (or a connection test) can't
    complete — bad credentials, a misconfigured repo/bucket, a network
    error, a provider-side API error. Surfaced to the admin as
    Integration.last_error rather than a raw traceback."""
