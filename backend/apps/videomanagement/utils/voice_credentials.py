import hashlib

from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.apikeysmanagement.models import ApiKeys, Provider


def key_fingerprint(key):
    return hashlib.sha256(key.encode()).hexdigest() if key else ""


def key_source(user):
    return "service" if user.use_service_api_keys else "user"


def voice_key(user, voice=None):
    if voice and (user is None or voice.created_by_id != user.pk):
        raise PermissionDenied("This voice belongs to another user.")
    key = ApiKeys.key_for(user, Provider.ELEVENLABS)
    if not key:
        raise ValidationError("An ElevenLabs API key is required. Check API keys and providers.")
    if voice and (
        voice.clone_key_source != key_source(user)
        or voice.clone_key_fingerprint != key_fingerprint(key)
    ):
        raise ValidationError("Switch back to the ElevenLabs key used to create this voice.")
    return key
