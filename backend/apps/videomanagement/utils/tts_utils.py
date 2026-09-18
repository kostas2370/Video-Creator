import base64
from dataclasses import dataclass
from typing import Union
import logging
import requests
from openai import OpenAI
from rest_framework import status
from rest_framework.exceptions import APIException
from .mapper import api_providers
from apps.apikeysmanagement.models import ApiKeys, Provider
import sys

logger = logging.getLogger(__name__)
thismodule = sys.modules[__name__]


@dataclass
class ApiSyn:
    provider: str
    path: str


def save(
    syn: Union[ApiSyn, None], text: str = "", save_path: str = "", user=None
) -> Union[str, None]:
    """
    Save synthesized audio to a file.

    Parameters:
    -----------
    syn : ApiSyn
        The synthesizer to use. Only API-backed voices are supported.
    text : str, optional
        The text to synthesize. Default is an empty string.
    save_path : str, optional
        The file path where the synthesized audio will be saved.

    Returns:
    --------
    str
        The file path to the saved audio file, or None if no synthesizer was given.

    Raises:
    -------
    APIException
        If the voice names a provider that is not in api_providers.

    Notes:
    ------
    - Every voice is an API call; see api_providers in mapper.py.
    """
    if syn is None:
        return None

    provider = api_providers.get(syn.provider)
    if provider is None:
        logger.error("Voice has unsupported provider %r", syn.provider)
        raise APIException(
            detail=f"Unsupported voice provider: {syn.provider}",
            code=status.HTTP_400_BAD_REQUEST,
        )

    getattr(thismodule, provider)(text, save_path, syn.path, user=user)

    return save_path


def tts_from_open_api(text, save_path, voice="onyx", user=None):
    """
    Generate speech audio from text using the OpenAI TTS API.

    Parameters:
    -----------
    text : str
        The text to convert into speech audio.
    voice : str, optional
        The voice to use for speech synthesis. Default is "onyx".

    Returns:
    --------
    OpenAIResponse
        The response object from the OpenAI TTS API.

    Notes:
    ------
    - This function interacts with the Official OpenAI TTS API to generate speech audio from text.
    """
    logger.warning("API CALL IN OFFICIAL GPT-TTS")

    client = OpenAI(api_key=ApiKeys.key_for(user, Provider.OPENAI))
    # Explicit wav: the API defaults to mp3, which this writes to a .wav path.
    response = client.audio.speech.create(
        model="tts-1", voice=voice, input=text, response_format="wav"
    )
    response.stream_to_file(save_path)

    return response


def tts_from_eleven_labs(text, save_path, voice, user=None):
    """
    Generate speech audio from text using the Eleven Labs Text-to-Speech (TTS) API.

    Parameters:
    -----------
    text : str
        The text to convert into speech audio.
    voice : str
        The voice to use for speech synthesis.

    Returns:
    --------
    requests.Response
        The response object from the Eleven Labs TTS API.

    Notes:
    ------
    - This function interacts with the Eleven Labs Text-to-Speech (TTS) API to generate speech audio from text.
    """

    logger.warning("API CALL IN ELEVEN-LABS")

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
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)

    except Exception as exc:
        logger.error(exc)

    return response


def tts_from_60db(text, save_path, voice, user=None):
    """
    Generate speech audio from text using the 60db Text-to-Speech (TTS) API.

    Parameters:
    -----------
    text : str
        The text to convert into speech audio.
    save_path : str
        The file path where the synthesized audio will be saved.
    voice : str
        The 60db voice_id to use for speech synthesis.

    Returns:
    --------
    requests.Response
        The response object from the 60db TTS API.

    Notes:
    ------
    - This function interacts with the 60db Text-to-Speech (TTS) API to generate speech audio from text.
    - Unlike Eleven Labs (which streams raw bytes), 60db returns a JSON payload containing the audio as a
      base64-encoded string under the `audio_base64` field, which is decoded and written to ``save_path``.
    - ``wav`` output is requested so the saved file matches the ``.wav`` extension used by the pipeline.
    """

    logger.warning("API CALL IN 60DB")

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
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        payload = response.json()
        audio_base64 = payload.get("audio_base64")
        if not audio_base64:
            raise ValueError(f"60db TTS returned no audio: {payload.get('message')}")

        with open(save_path, "wb") as f:
            f.write(base64.b64decode(audio_base64))

    except Exception as exc:
        logger.error(exc)

    return response
