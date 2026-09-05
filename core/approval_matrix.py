"""The Approval Matrix's actual enforcement — a single function every
gated call site checks before writing its own ElectronicSignature. See
ApprovalMatrixRule's docstring (core/models.py) for the design: additive,
off by default, invisible to any entity type nobody configures a rule
for."""


class ApprovalRequiredError(Exception):
    """Raised by assert_approval_gate when a rule is configured but no
    matching ApprovalRecord exists yet. Callers catch this and surface it
    as a 403 rather than letting a closing action through."""

    def __init__(self, required_role):
        self.required_role = required_role
        super().__init__(f'This action requires prior approval from a {required_role}.')


def assert_approval_gate(entity_type, object_id):
    from .models import ApprovalMatrixRule, ApprovalRecord

    rule = ApprovalMatrixRule.objects.filter(entity_type=entity_type, active=True).first()
    if not rule:
        return  # No rule configured — behaves identically to before this feature existed.

    if not ApprovalRecord.objects.filter(entity_type=entity_type, object_id=object_id).exists():
        raise ApprovalRequiredError(rule.required_role)
