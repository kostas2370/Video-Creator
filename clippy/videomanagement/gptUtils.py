import g4f
import json
from prompt_utils import format_prompt
from ttsUtils import create_model, save
import os
from slugify import slugify


def get_reply(prompt, format="json"):
    g4f.logging = True  # enable logging
    g4f.check_version = False

    response = g4f.ChatCompletion.create(model = "gpt-3.5-turbo", messages = [{"content": prompt}], stream = True, )
    x = ""
    for message in response:
        x += message
    if format == "json":

        return json.loads(x)

    return x


def make_video():
    message = format_prompt("educational",
                            reply_format = 'json {"title": -,"target_audience": -,"topic": -,"scenes": [{"scene": -"dialogue": -"image_description"	: - (only text)}]}',
                            userPrompt = "A video about  basic physics in school, i want it to be enthusiastic ",
                            title = "physics")
    x = get_reply(message)
    syn = create_model()
    os.mkdir(slugify(x["title"]))
    for j in x["scenes"]:
        save(syn, j["dialogue"], save_path = f'{slugify(x["title"])}/{j["scene"]}.wav')

make_video()
