from TTS.utils.synthesizer import Synthesizer
from TTS.utils.manage import ModelManager
import os
from typing import Union

from .gpt_utils import tts_from_open_api, tts_from_eleven_labs
from dataclasses import dataclass


@dataclass
class ApiSyn:
    provider: str
    path: str


def create_model(model_path: str = rf"{os.path.abspath(os.getcwd())}\.models.json",
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

    return syn


def save(syn: Union[Synthesizer, ApiSyn], text: str = "", save_path: str = "") -> str:
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
    if type(syn) is Synthesizer:
        outputs = syn.tts(text)
        syn.save_wav(outputs, save_path)

    if type(syn) is ApiSyn:
        if syn.provider == "open_ai":
            resp = tts_from_open_api(text, syn.path)
            resp.stream_to_file(save_path)

        if syn.provider == "eleven_labs":
            resp = tts_from_eleven_labs(text, syn.path)
            with open(save_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size = 1024):
                    if chunk:
                        f.write(chunk)

    return save_path
