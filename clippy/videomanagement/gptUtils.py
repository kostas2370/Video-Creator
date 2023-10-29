import g4f
import json


def get_reply(prompt, format = "json"):
    g4f.logging = True  # enable logging
    g4f.check_version = False

    response = g4f.ChatCompletion.create(model = "gpt-3.5-turbo", messages = [{"content": prompt}], stream = True, )
    x = ""
    for message in response:
        x += message
    if format == "json":
        return json.load(x)

    return x