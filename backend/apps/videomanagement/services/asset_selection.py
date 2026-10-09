from django.core.exceptions import ValidationError
from rest_framework.exceptions import NotFound


def owned_asset(model, selection, owner):
    """Resolve a private asset before changing a video or starting generation."""
    if selection in (None, "", "None", "null"):
        return None
    try:
        return model.objects.get(pk=selection, created_by=owner)
    except (model.DoesNotExist, ValueError, TypeError, ValidationError):
        raise NotFound(f"{model.__name__} is unavailable.")


def available_voice(selection, owner):
    from ..models import VoiceModel

    if selection in (None, ""):
        return None
    try:
        return VoiceModel.available_to(owner).get(pk=selection)
    except (VoiceModel.DoesNotExist, ValueError, TypeError, ValidationError):
        raise NotFound("Voice is unavailable.")
