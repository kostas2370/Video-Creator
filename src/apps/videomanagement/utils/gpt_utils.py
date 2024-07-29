import io
import json
import logging
import sys

import g4f
import requests
from django.conf import settings
from openai import OpenAI
import anthropic

from .exceptions import InvalidJsonFormatError
import google.generativeai as genai
from .mapper import model_calls

logger = logging.getLogger(__name__)
thismodule = sys.modules[__name__]


def check_json(json_file: json) -> bool:
    """
    Check if the provided JSON file has the required structure.

    Parameters:
    -----------
    json_file : dict
        The JSON data to be validated.

    Returns:
    --------
    bool
        True if the JSON file has the required structure, False otherwise.

    Detailed Steps:
    ---------------
    1. Check if the 'scenes' key exists in the JSON file.
    2. Check if the 'title' key exists in the JSON file.
    3. Check if the 'scenes' list is not empty.
    4. Check if the 'scene' key exists in the first item of the 'scenes' list.

    Notes:
    ------
    - This function validates the structure of a JSON file to ensure it contains necessary elements.
    """
    if "scenes" not in json_file:
        return False

    if "title" not in json_file:
        return False

    if len(json_file['scenes']) == 0:
        return False

    if "scene" not in json_file['scenes'][0]:
        return False

    return True


def official_gpt_call(prompt: str, gpt_model=None):
    x = io.StringIO()
    logger.warning("API CALL IN OFFICIAL GPT")

    client = OpenAI(api_key = settings.OPEN_API_KEY)

    stream = client.chat.completions.create(model = settings.DEFAULT_GPT_MODEL if not gpt_model else gpt_model,
                                            messages = [{"role": "assistant", "content": prompt}, ], stream = True,
                                            max_tokens = settings.MAX_TOKENS)

    for chunk in stream:
        x.write(chunk.choices[0].delta.content or "")

    return x


def g4f_gpt_call(prompt: str, gpt_model="gpt-4"):
    x = io.StringIO()
    logger.info("api call in gpt4free")

    gpt_model = g4f.models.gpt_4_turbo if gpt_model == "gpt-4" else 'gpt-3.5-turbo'
    response = g4f.ChatCompletion.create(model = gpt_model, messages = [{"content": prompt}], stream = True, )

    for message in response:
        x.write(message)

    return x


def gemini_call(prompt: str, model='gemini-1.5-pro'):
    x = io.StringIO()
    genai.configure(api_key = settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(model)
    response = model.generate_content(prompt)
    for chunk in response:
        x.write(chunk)

    return x


def claude_call(prompt: str, model="claude-3-5-sonnet-20240620"):
    x = io.StringIO()
    client = anthropic.Anthropic(settings.ANTHROPIC_API_KEY)
    message = client.messages.create(model = model,
                                     max_tokens = 1000,
                                     temperature = 0,
                                     system = "You are a world-class poet. Respond only with short poems.",
                                     messages = [{"role": "assistant", "content": [{"type": "text", "text": prompt}]}])

    x.write(message.content[0].text)
    return x


def gpt_call(prompt, gpt_model):
    if not settings.GPT_OFFICIAL:
        x = g4f_gpt_call(prompt = prompt, gpt_model = gpt_model)
    else:
        x = official_gpt_call(prompt = prompt)

    return x


def get_reply(prompt, time=0, reply_format="json", model='gpt-4'):
    """
    Get a reply to a prompt from either GPT-4 Free or the OpenAI API.

    Parameters:
    -----------
    prompt : list of str
        The prompt for the model. For GPT-4 Free, it should contain a single prompt string.
        For the OpenAI API, it should contain two strings representing the user's and assistant's messages.
    time : int, optional
        The current retry attempt. Default is 0.
    reply_format : str, optional
        The format of the reply. Default is "json".
    gpt_model : str, optional
        The GPT model to use. Default is 'gpt-4'.

    Returns:
    --------
    dict or str
        The reply in JSON format if 'reply_format' is "json", otherwise a string.

    Raises:
    -------
    Exception
        If the maximum retry limit (5) is reached.

    Notes:
    ------
    - This function interacts with either GPT-4 Free or the OpenAI API to generate replies to prompts.
    """
    time += 1
    g4f.logging = True
    g4f.check_version = False

    for key, call in model_calls.items():
        if key in model:
            x = getattr(thismodule, call)(prompt, model)
            break

    if reply_format == "json":
        x = x.getvalue()
        x = x[x.index('{'):len(x)-(x[::-1].index('}'))]

        try:

            js = json.loads(x)
            if not check_json(js):
                raise InvalidJsonFormatError()

            return js

        except InvalidJsonFormatError:
            if time == 5:
                raise Exception("Max gpt limit is 5 , try again with different prompt !!")

            return get_reply(prompt, time = time, gpt_model = model)

    return x


def get_update_sentence(prompt):
    """
    Generate an updated sentence based on the given prompt using GPT-3.5 from GPT-4 Free.

    Parameters:
    -----------
    prompt : str
        The prompt for generating the updated sentence.

    Returns:
    --------
    str
        The updated sentence generated by the model.

    Notes:
    ------
    - This function interacts with GPT-4 Free to generate an updated sentence based on the given prompt.
    """
    response = g4f.ChatCompletion.create(model = 'gpt-3.5-turbo', messages = [{"content": prompt}], stream = True, )
    x = io.StringIO()
    for message in response:
        x.write(message)

    return x.getvalue()


def select_from_vision(prompt, images):
    logger.warning("API CALL IN OFFICIAL GPT vision")

    client = OpenAI(api_key = settings.OPEN_API_KEY)

    messages = [{"role": "user", "content": [{"type": "text",
                                              "text": f"I will send you 3 images, i want you to pick 1 , that is closer"
                                                      f" on this prompt : {prompt}."
                                                      f"Answer me with a number from 1 to 3 "}, ], }]

    for x in images:
        dicts = {"type": "image_url",
                 "image_url": {"url": x}}
        messages[0]['content'].append(dicts)

    response = client.chat.completions.create(model = "gpt-4-vision-preview", messages = messages, max_tokens = 300, )
    x = response.choices[0].message.content

    x = 0 if '1' in x else 1 if '2' in x else 2

    return x


def tts_from_open_api(text, voice="onyx"):
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
    print(f"Text : {text}")
    response = client.audio.speech.create(model = "tts-1", voice = voice, input = text)
    return response


def tts_from_eleven_labs(text, voice):
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

    response = requests.post(url, json = data, headers = headers)

    return response


def get_voices_from_labs():
    url = "https://api.elevenlabs.io/v1/voices"
    headers = {"Accept": "application/json", "xi-api-key": settings.XI_API_KEY, "Content-Type": "application/json"}

    response = requests.get(url, headers = headers)
    return response.json()['voices']
