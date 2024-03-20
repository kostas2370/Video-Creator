from TTS.utils.synthesizer import Synthesizer
from TTS.utils.manage import ModelManager
import os

from .gpt_utils import tts_from_open_api
from dataclasses import dataclass


@dataclass
class ApiSyn:
    provider: str
    path: str


def create_model(model_path=rf"{os.path.abspath(os.getcwd())}\.models.json",
                 model="tts_models/en/ljspeech/vits--neon", vocoder="default_vocoder"):

    model_manager = ModelManager(model_path)
    model_path, config_path, model_item = model_manager.download_model(model)
    if vocoder == "default_vocoder" and model_item.get(vocoder) is not None:
        voc_path, voc_config_path, _ = model_manager.download_model(model_item[vocoder])

    elif vocoder is not None:
        try:
            voc_path, voc_config_path, _ = model_manager.download_model(vocoder)

        except Exception:
            voc_path, voc_config_path, _ = None, None, None
            print(Exception)
    else:
        voc_path, voc_config_path = None, None

    if voc_path is not None and voc_config_path is not None:
        syn = Synthesizer(tts_checkpoint = model_path, tts_config_path = config_path, vocoder_checkpoint = voc_path,
                          vocoder_config = voc_config_path)

    else:
        syn = Synthesizer(tts_checkpoint = model_path, tts_config_path = config_path)

    return syn


def save(syn, text="", save_path=""):

    if type(syn) is Synthesizer:

        outputs = syn.tts(text)
        syn.save_wav(outputs, save_path)

    if type(syn) is ApiSyn:
        resp = tts_from_open_api(text, syn.path)
        resp.stream_to_file(save_path)

    return save_path
