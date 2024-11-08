import os
from dataclasses import dataclass
from typing import Union
import logging
import requests
from TTS.utils.manage import ModelManager
from TTS.utils.synthesizer import Synthesizer
from django.conf import settings
from openai import OpenAI
from .mapper import api_providers
import sys

logger = logging.getLogger(__name__)
thismodule = sys.modules[__name__]

@dataclass
class ApiSyn:
    provider: str
    path: str


def create_model(model_path: str = f"{os.path.abspath(os.getcwd())}/.models.json",
                 model: str = "tts_models/en/ljspeech/vits--neon", vocoder: str = "default_vocoder") -> Synthesizer:

    """
    Create and return a Synthesizer instance with specified model and vocoder settings.

    Parameters:
    -----------
    model_path : str, optional
        The file path to the model manager configuration. Default is the current working directory with `.models.json`.
    model : str, optional
        The model to be used for the text-to-speech synthesis. Default is "tts_models/en/ljspeech/vits--neon".
    vocoder : str, optional
        The vocoder to be used. If "default_vocoder" and available in the model, it will be used. Default is "default_vocoder".

    Returns:
    --------
    Synthesizer
        An instance of the Synthesizer class initialized with the specified model and vocoder.

    Detailed Steps:
    ---------------
    1. Initialize the ModelManager with the given model path.
    2. Download the specified model using the ModelManager.
    3. Download the vocoder model if specified, falling back to the default vocoder if necessary.
    4. Initialize the Synthesizer with the downloaded model and vocoder configurations.

    Notes:
    ------
    - Requires the `Synthesizer` and `ModelManager` classes from the appropriate library.
    - The function assumes that the model and vocoder names provided are valid and available for download.
    - The function prints an error message if the specified vocoder cannot be downloaded, and proceeds without a vocoder.
    """
    try:
        model_manager = ModelManager(model_path)
        model_path, config_path, model_item = model_manager.download_model(model)
        if vocoder == "default_vocoder" and model_item.get(vocoder) is not None:
            voc_path, voc_config_path, _ = model_manager.download_model(model_item[vocoder])

        elif vocoder is not None:
            try:
                voc_path, voc_config_path, _ = model_manager.download_model(vocoder)

            except Exception as ex:
                voc_path, voc_config_path, _ = None, None, None
                print(ex)
        else:
            voc_path, voc_config_path = None, None

        if voc_path is not None and voc_config_path is not None:
            syn = Synthesizer(tts_checkpoint = model_path, tts_config_path = config_path, vocoder_checkpoint = voc_path,
                              vocoder_config = voc_config_path)

        else:
            syn = Synthesizer(tts_checkpoint = model_path, tts_config_path = config_path)

    except Exception as exc:
        print(exc)
        syn = None

    return syn


def save(syn: Union[ApiSyn, Synthesizer], text: str = "", save_path: str = "") -> str:
    """
    Save synthesized audio to a file.

    Parameters:
    -----------
    syn : Union[Synthesizer, ApiSyn]
        The synthesizer object to use for audio synthesis.
    text : str, optional
        The text to synthesize. Default is an empty string.
    save_path : str, optional
        The file path where the synthesized audio will be saved. If not provided, a unique filename will be generated in the current directory.

    Returns:
    --------
    str
        The file path to the saved audio file.

    Raises:
    -------
    ValueError
        If an unsupported synthesizer type is provided.

    Detailed Steps:
    ---------------
    1. Check the type of synthesizer object provided.
    2. If it's a Synthesizer object, synthesize the text using the Synthesizer's `tts` method and save the output to the specified path.
    3. If it's an ApiSyn object, determine the provider and call the appropriate API function to synthesize the text.
    4. Save the synthesized audio to the specified path.

    Notes:
    ------
    - Requires the `Synthesizer` and `ApiSyn` classes from the appropriate library.
    - The function assumes that the provided synthesizer objects have appropriate methods for text-to-speech synthesis.
    - If `save_path` is not provided, the audio will be saved with a unique filename in the current directory.
    """
    if syn is None:
        return None

    if type(syn) is ApiSyn:
        resp = getattr(thismodule, api_providers.get(syn.provider))(text, save_path, syn.path)

    else:
        outputs = syn.tts(text)
        syn.save_wav(outputs, save_path)

    return save_path


def tts_from_open_api(text, save_path, voice="onyx"):
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

    client = OpenAI(api_key = settings.OPEN_API_KEY)
    response = client.audio.speech.create(model = "tts-1", voice = voice, input = text)
    response.stream_to_file(save_path)

    return response


def tts_from_eleven_labs(text, save_path, voice):
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

    headers = {"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": settings.XI_API_KEY}
    data = {"text": text, "model_id": "eleven_monolingual_v1",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.5}}

    try:
        response = requests.post(url, json = data, headers = headers)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size = 1024):
                if chunk:
                    f.write(chunk)

    except Exception as exc:
        logger.error(exc)

    return response
