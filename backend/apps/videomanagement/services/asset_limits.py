from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.exceptions import ValidationError

MAX_CLIPS_PER_USER = 5


def save_limited_clip(serializer, user):
    """Save an intro/outro while enforcing the per-user cap atomically."""
    model = serializer.Meta.model
    label = model._meta.verbose_name.lower()
    with transaction.atomic():
        # Serialize clip uploads for this account so simultaneous requests cannot
        # both observe a free slot and push the user over the limit.
        get_user_model().objects.select_for_update().get(pk=user.pk)
        if model.objects.filter(created_by=user).count() >= MAX_CLIPS_PER_USER:
            raise ValidationError(
                {
                    "detail": (
                        f"You can store up to {MAX_CLIPS_PER_USER} {label} clips. "
                        "Delete one before uploading another."
                    )
                }
            )
        return serializer.save(created_by=user)
