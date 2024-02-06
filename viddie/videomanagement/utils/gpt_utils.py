"""
Viddie is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as
published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

Viddie is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import io
import json

import g4f
from django.conf import settings
from openai import OpenAI

from .exceptions import InvalidJsonFormatError


def check_json(json_file):
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

    gpt_model = g4f.models.gpt_4 if gpt_model == "gpt-4" else 'gpt-3.5-turbo'

    response = g4f.ChatCompletion.create(model = gpt_model, messages = [{"content": prompt}], stream = True, )
    x = io.StringIO()
    for message in response:
        x.write(message)

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


def get_reply_from_official_api(prompt, time=1):
    time += 1
    client = OpenAI(api_key = settings.OPEN_API_KEY)

    stream = client.chat.completions.create(model = "gpt-4", messages = [{"role": "assistant", "content": prompt[0]},
                                                                         {"role": "user", "content": prompt[1]}],
                                            stream = True, max_tokens = settings.MAX_TOKENS)

    x = io.StringIO()

    for chunk in stream:
        x.write(chunk.choices[0].delta.content or "")

    try:
        x = x.getvalue()
        print(x)
        x = x[x.index('{'):len(x)-(x[::-1].index('}'))]

        js = json.loads(x)
        if not check_json(js):
            raise InvalidJsonFormatError()

        return js

    except InvalidJsonFormatError:
        if time == 5:
            raise Exception("Max gpt limit is 5 , try again with different prompt !!")

        return get_reply_from_official_api(prompt, time = time)


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
    print(messages)
    print(x)

    x = 0 if '1' in x else 1 if '2' in x else 2

    return x


def tts_from_open_api(text, voice = "onyx"):
    client = OpenAI(api_key = settings.OPEN_API_KEY)
    response = client.audio.speech.create(model = "tts-1", voice = voice, input = text)
    return response
