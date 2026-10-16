"""Private ElevenLabs clones. Uploaded samples are transient, never media assets."""

import hashlib
import logging
import subprocess
import tempfile
import wave

import requests
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from apps.apikeysmanagement.models import ApiKeys, Provider
from ..models import VoiceModel, VoiceModelType
from ..utils.usage import record_usage

logger = logging.getLogger(__name__)
BASE_URL = "https://api.elevenlabs.io/v1"
MAX_VOICES = 3
PREVIEW_TEXT = "Hello! This is my custom voice, ready to bring my next video to life."


class VoiceProviderError(APIException):
    status_code = 502
    default_detail = "ElevenLabs could not complete the request. Please try again."


def key_fingerprint(key):
    return hashlib.sha256(key.encode()).hexdigest() if key else ""


def key_source(user):
    return "service" if user.use_service_api_keys else "user"


def voice_key(user, voice=None):
    key = ApiKeys.key_for(user, Provider.ELEVENLABS)
    if not key:
        raise ValidationError("An ElevenLabs API key is required. Check API keys and providers.")
    if voice and (
        voice.clone_key_source != key_source(user)
        or voice.clone_key_fingerprint != key_fingerprint(key)
    ):
        raise ValidationError("Switch back to the ElevenLabs key used to create this voice.")
    return key


def provider_request(method, path, key, **kwargs):
    try:
        response = requests.request(
            method, f"{BASE_URL}/{path}", headers={"xi-api-key": key},
            timeout=(10, 90), **kwargs,
        )
        if method == "DELETE" and response.status_code == 404:
            return response
        response.raise_for_status()
        return response
    except requests.RequestException as exc:
        response = getattr(exc, "response", None)
        code = response.status_code if response is not None else None
        # Do not expose provider responses, which may contain account details.
        if code in (401, 403):
            raise VoiceProviderError("ElevenLabs denied access. Check the key, permissions, and voice-cloning plan.") from exc
        if code == 429:
            raise VoiceProviderError("ElevenLabs has reached an account or usage limit. Please try later.") from exc
        if code in (400, 422):
            raise VoiceProviderError("ElevenLabs could not use this sample. Try a clear recording of only your voice, and check available voice slots.") from exc
        raise VoiceProviderError() from exc


def provider_json(response):
    try:
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError()
        return data
    except ValueError as exc:
        raise VoiceProviderError() from exc


def normalized_sample(upload):
    """Decode untrusted uploads with bounded time and local-file protocols only."""
    with tempfile.NamedTemporaryFile(suffix=".input") as source, tempfile.NamedTemporaryFile(suffix=".wav") as output:
        for chunk in upload.chunks():
            source.write(chunk)
        source.flush()
        try:
            subprocess.run(
                ["ffmpeg", "-nostdin", "-v", "error", "-y", "-protocol_whitelist", "file,pipe",
                 "-i", source.name, "-map", "0:a:0", "-vn", "-t", "121", "-ac", "1",
                 "-ar", "22050", "-c:a", "pcm_s16le", output.name],
                capture_output=True, timeout=30, check=True,
            )
            with wave.open(output.name, "rb") as audio:
                duration = audio.getnframes() / audio.getframerate()
            # Browser recording timers and codec padding can add a fraction of a second.
            if not 10 <= duration <= 120.5:
                raise ValidationError({"file": "Use a recording between 10 seconds and 2 minutes."})
            output.seek(0)
            return output.read()
        except (OSError, subprocess.SubprocessError, wave.Error, EOFError) as exc:
            raise ValidationError({"file": "This file could not be read as audio. Try WAV, MP3, M4A, or WebM."}) from exc


def create_clone(user, name, upload):
    key = voice_key(user)
    audio = normalized_sample(upload)
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=user.pk)
        if VoiceModel.objects.filter(created_by=user, is_cloned=True).count() >= MAX_VOICES:
            raise ValidationError(f"You can keep up to {MAX_VOICES} custom voices. Delete one to add another.")
        data = provider_json(provider_request(
            "POST", "voices/add", key, data={"name": name},
            files=[("files", ("sample.wav", audio, "audio/wav"))],
        ))
        remote_id = data.get("voice_id")
        if not isinstance(remote_id, str) or not remote_id or len(remote_id) > 255 or not remote_id.isalnum():
            raise VoiceProviderError()
        try:
            return VoiceModel.objects.create(
                created_by=user, name=name, provider=Provider.ELEVENLABS,
                type=VoiceModelType.API, path=remote_id, is_cloned=True,
                clone_key_source=key_source(user), clone_key_fingerprint=key_fingerprint(key),
                consented_at=timezone.now(), requires_verification=data.get("requires_verification") is not False,
            )
        except Exception:
            try:
                provider_request("DELETE", f"voices/{remote_id}", key)
            except APIException:
                logger.error("Could not remove orphaned custom voice %s", remote_id)
            raise


def preview_clone(user, voice):
    key = voice_key(user, voice)
    if voice.requires_verification:
        raise ValidationError("This voice requires verification in ElevenLabs before it can be used.")
    response = provider_request(
        "POST", f"text-to-speech/{voice.path}", key,
        json={"text": PREVIEW_TEXT, "model_id": "eleven_multilingual_v2"},
    )
    if not response.content or "audio/" not in response.headers.get("Content-Type", ""):
        raise VoiceProviderError()
    record_usage(user, "tts", Provider.ELEVENLABS, "eleven_multilingual_v2", characters=len(PREVIEW_TEXT))
    return response.content


def refresh_clone(user, voice):
    key = voice_key(user, voice)
    data = provider_json(provider_request("GET", f"voices/{voice.path}", key))
    # Missing verification details must never silently unlock a pending voice.
    verification = data.get("voice_verification") or {}
    if not isinstance(verification, dict):
        raise VoiceProviderError()
    if "requires_verification" in verification:
        voice.requires_verification = bool(verification["requires_verification"])
    elif verification.get("is_verified") is True:
        voice.requires_verification = False
    voice.save(update_fields=["requires_verification"])


def delete_clone(user, voice):
    key = voice_key(user, voice)
    provider_request("DELETE", f"voices/{voice.path}", key)
    voice.delete()
