"""
Viddie is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as
published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

Viddie is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""


from TTS.utils.synthesizer import Synthesizer
from TTS.utils.manage import ModelManager
import os
import pyttsx3


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

    if type(syn) is int or type(syn) is str:
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        engine.setProperty('voice', voices[int(syn)].id)
        engine.save_to_file(text, save_path)
        engine.runAndWait()

    return save_path
