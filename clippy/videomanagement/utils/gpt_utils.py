import g4f
import json


def check_json(json_file):
    if "scenes" not in json_file:
        return False

    if "title" not in json_file:
        return False

    if len(json_file['scenes']) == 0:
        return False

    if "dialogue" not in json_file['scenes'][0]:
        return False

    return True


def get_reply(prompt, time=0, reply_format="json", gpt_model='gpt-3.5-turbo'):
    time += 1
    g4f.logging = True  # enable logging
    g4f.check_version = False
    if gpt_model == "gpt-4":
        gpt_model = g4f.models.gpt_4

    response = g4f.ChatCompletion.create(model = gpt_model, messages = [{"content": prompt}], stream = True, )
    x = ""
    for message in response:
        x += message

    if reply_format == "json":


        x = x[x.index('{'):len(x) - (x[::-1].index('}'))]
        print(x)
        try:

            js = json.loads(x)

            if not check_json(js):
                raise Exception('Wrong format in dialogue')

            return js

        except Exception:
            if time == 5:
                raise Exception("Max gpt limit is 5 , try again with different prompt !!")

            return get_reply(prompt, time = time)
    return x
