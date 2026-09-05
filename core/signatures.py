"""Creates 21 CFR Part 11 electronic signature records. See
core.models.ElectronicSignature for what makes this a "signature" rather
than just another log entry: password re-verification happens at the
call site (WorkflowStepViewSet.decide) before this is ever called."""


def create_signature(user, meaning, target):
    from django.contrib.contenttypes.models import ContentType
    from .models import ElectronicSignature

    signature = ElectronicSignature(
        user=user,
        printed_name=user.get_full_name() or user.username,
        meaning=meaning,
        content_type=ContentType.objects.get_for_model(target),
        object_id=target.pk,
        target_repr=str(target),
    )
    signature.save()
    return signature
