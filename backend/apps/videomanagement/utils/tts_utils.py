import base64
import logging
import os
import sys
from dataclasses import dataclass
from typing import Optional, Union, Any

import requests
from openai import OpenAI
from rest_framework import status
from rest_framework.exceptions import APIException

from apps.apikeysmanagement.models import ApiKeys, Provider, UserCustomTTSProvider

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30


class TTSRegistry:
    _providers = {}
    _fallback_provider = None

    @classmethod
    def register(cls, name: str):
        def decorator(func):
            cls._providers[name] = func.__name__
            return func

        return decorator

    @classmethod
    def register_fallback(cls):
        def decorator(func):
            cls._fallback_provider = func.__name__
            return func

        return decorator

    @classmethod
    def get(cls, name: str):
        func_name = cls._providers.get(name) or cls._fallback_provider
        if not func_name:
            return None
        return getattr(sys.modules[__name__], func_name, None)


@dataclass
class ApiSyn:
    provider: str
    path: str


@TTSRegistry.register(Provider.OPENAI)
def tts_from_openai(
    text: str, save_path: str, voice: str = "onyx", user=None, **kwargs
) -> Any:
    logger.warning("API CALL IN OpenAI TTS")

    client = OpenAI(api_key=ApiKeys.key_for(user, Provider.OPENAI))
    response = client.audio.speech.create(
        model="tts-1", voice=voice, input=text, response_format="wav"
    )
    response.stream_to_file(save_path)

    return response


@TTSRegistry.register(Provider.ELEVENLABS)
def tts_from_elevenlabs(
    text: str, save_path: str, voice: str, user=None, **kwargs
) -> Optional[requests.Response]:
    logger.warning("API CALL IN ElevenLabs TTS")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ApiKeys.key_for(user, Provider.ELEVENLABS),
    }
    data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.5},
    }

    response = None
    try:
        response = requests.post(
            url, json=data, headers=headers, timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
    except Exception as exc:
        logger.error("ElevenLabs TTS request failed: %s", exc)

    return response


@TTSRegistry.register(Provider.SIXTYDB)
def tts_from_sixtydb(
    text: str, save_path: str, voice: str, user=None, **kwargs
) -> Optional[requests.Response]:
    logger.warning("API CALL IN 60dB TTS")

    url = "https://api.60db.ai/tts-synthesize"
    headers = {
        "Authorization": f"Bearer {ApiKeys.key_for(user, Provider.SIXTYDB)}",
        "Content-Type": "application/json",
    }
    data = {
        "text": text,
        "voice_id": voice,
        "output_format": "wav",
        "enhance": True,
        "speed": 1,
        "stability": 50,
        "similarity": 75,
    }

    response = None
    try:
        response = requests.post(
            url, json=data, headers=headers, timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        payload = response.json()
        audio_base64 = payload.get("audio_base64")
        if not audio_base64:
            raise ValueError(f"60dB TTS returned no audio: {payload.get('message')}")

        with open(save_path, "wb") as f:
            f.write(base64.b64decode(audio_base64))
    except Exception as exc:
        logger.error("60dB TTS request failed: %s", exc)

    return response


@TTSRegistry.register_fallback()
def tts_from_custom_provider(
    text: str,
    save_path: str,
    voice: str,
    user=None,
    provider_name: Optional[str] = None,
) -> Optional[requests.Response]:
    logger.warning("API CALL IN USER CUSTOM TTS: %s", provider_name)

    if not user or not provider_name:
        raise APIException(
            detail=f"Custom provider '{provider_name}' not found for this user.",
            code=status.HTTP_404_NOT_FOUND,
        )

    try:
        provider_config = UserCustomTTSProvider.objects.get(
            user=user, name=provider_name
        )
    except UserCustomTTSProvider.DoesNotExist:
        raise APIException(
            detail=f"Custom provider '{provider_name}' not found for this user.",
            code=status.HTTP_404_NOT_FOUND,
        )

    headers, auth = provider_config.get_auth_headers()
    data = provider_config.request_payload(
        {
            provider_config.text_field_name: text,
            provider_config.voice_field_name: voice,
        }
    )

    response = None
    try:
        response = requests.post(
            provider_config.endpoint_url,
            json=data,
            headers=headers,
            auth=auth,
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()

        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
    except Exception as exc:
        if os.path.exists(save_path):
            os.remove(save_path)
        logger.error(
            "Error generating audio from custom provider '%s': %s",
            provider_name,
            exc,
        )

    return response


def save(
    syn: Union[ApiSyn, None], text: str = "", save_path: str = "", user=None
) -> Union[str, None]:
    if not syn:
        return None

    handler = TTSRegistry.get(syn.provider)
    if not handler:
        logger.error("No TTS handler registered for provider: %s", syn.provider)
        return None

    handler(
        text,
        save_path,
        syn.path,
        user=user,
        provider_name=syn.provider,
    )

    if not os.path.exists(save_path) or os.path.getsize(save_path) == 0:
        logger.error("%s wrote no audio for %r", syn.provider, save_path)
        return None

    return save_path


def get_voices_from_elevenlabs(user=None, **kwargs) -> list:
    url = "https://api.elevenlabs.io/v1/voices"
    headers = {
        "Accept": "application/json",
        "xi-api-key": ApiKeys.key_for(user, Provider.ELEVENLABS),
        "Content-Type": "application/json",
    }
    response = requests.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.json().get("voices", [])


def get_voices_from_sixtydb(user=None, **kwargs) -> list:
    url = "https://api.60db.ai/myvoices"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {ApiKeys.key_for(user, Provider.SIXTYDB)}",
        "Content-Type": "application/json",
    }
    response = requests.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.json().get("data", [])


def get_voices_from_custom_provider(
    user=None, custom_provider_name: str = None
) -> None:
    custom_provider = UserCustomTTSProvider.objects.get(
        user=user, name=custom_provider_name
    )
    if not custom_provider.voices_url:
        return
    try:
        response = requests.get(custom_provider.voices_url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        voices_list = (
            data
            if isinstance(data, list)
            else (data.get("voices") or data.get("data") or [])
        )
        return voices_list
    except Exception as exc:
        logger.error(
            "Failed to fetch voices for custom provider %s: %s",
            custom_provider.name,
            exc,
        )
