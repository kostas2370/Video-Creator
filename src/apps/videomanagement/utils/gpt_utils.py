import io
import json

import g4f
from django.conf import settings
from openai import OpenAI

from .exceptions import InvalidJsonFormatError
import requests
from django.conf import settings


def check_json(json_file: json) -> bool:
    if "scenes" not in json_file:
        return False

    if "title" not in json_file:
        return False

    if len(json_file['scenes']) == 0:
        return False

    if "scene" not in json_file['scenes'][0]:
        return False

    return True


def get_reply(prompt, time=0, reply_format="json", gpt_model='gpt-4'):
    time += 1
    g4f.logging = True  # enable logging
    g4f.check_version = False
    x = io.StringIO()

    if not settings.GPT_OFFICIAL:

        gpt_model = g4f.models.gpt_4 if gpt_model == "gpt-4" else 'gpt-3.5-turbo'
        response = g4f.ChatCompletion.create(model = gpt_model, messages = [{"content": prompt}], stream = True,
                                             )

        for message in response:
            x.write(message)

    else:
        client = OpenAI(api_key = settings.OPEN_API_KEY)

        stream = client.chat.completions.create(model = "gpt-4",
                                                messages = [{"role": "assistant", "content": prompt[0]},
                                                            {"role": "user", "content": prompt[1]}], stream = True,
                                                max_tokens = settings.MAX_TOKENS)

        for chunk in stream:
            x.write(chunk.choices[0].delta.content or "")

    if reply_format == "json":
        x = x.getvalue()
        print(x)
        x = x[x.index('{'):len(x)-(x[::-1].index('}'))]

        try:

            js = json.loads(x)
            if not check_json(js):
                raise InvalidJsonFormatError()

            return js

        except InvalidJsonFormatError:
            if time == 5:
                raise Exception("Max gpt limit is 5 , try again with different prompt !!")

            return get_reply(prompt, time = time, gpt_model = gpt_model)

    return x


def get_update_sentence(prompt):
    response = g4f.ChatCompletion.create(model = 'gpt-3.5-turbo', messages = [{"content": prompt}], stream = True, )
    x = io.StringIO()
    for message in response:
        x.write(message)

    return x.getvalue()


def select_from_vision(prompt, images):
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

    client = OpenAI(api_key = settings.OPEN_API_KEY)
    print(f"Text : {text}")
    response = client.audio.speech.create(model = "tts-1", voice = voice, input = text)
    return response


def tts_from_eleven_labs(text, voice):
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
