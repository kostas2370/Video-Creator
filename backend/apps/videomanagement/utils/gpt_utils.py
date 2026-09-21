import io
import json
import logging
import sys

import g4f
import requests
from django.conf import settings
from openai import OpenAI
import anthropic
from rest_framework.exceptions import APIException
from rest_framework import status


from .exceptions import InvalidJsonFormatException
from apps.apikeysmanagement.models import ApiKeys, Provider
import google.generativeai as genai

logger = logging.getLogger(__name__)
thismodule = sys.modules[__name__]

model_calls = (
    ("claude", "claude_call"),
    ("gemini", "gemini_call"),
    ("gpt", "official_gpt_call"),
    ("o1", "official_gpt_call"),
    ("o3", "official_gpt_call"),
    ("o4", "official_gpt_call"),
)


def token_limit_kwarg(model: str) -> dict:
    return {
        "max_completion_tokens": settings.MAX_TOKENS
        + settings.REASONING_TOKEN_ALLOWANCE
    }


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

    if len(json_file["scenes"]) == 0:
        return False

    if "scene" not in json_file["scenes"][0]:
        return False

    return True


def official_gpt_call(prompt: str, gpt_model=None, user=None):
    x = io.StringIO()
    logger.warning("API CALL IN OFFICIAL GPT")
    model = gpt_model or settings.DEFAULT_GPT_MODEL
    try:
        client = OpenAI(api_key=ApiKeys.key_for(user, Provider.OPENAI))
        stream = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "assistant", "content": prompt},
            ],
            stream=True,
            **token_limit_kwarg(model),
        )

        for chunk in stream:
            x.write(chunk.choices[0].delta.content or "")

    except Exception as err:
        logger.error(err)
        raise APIException(detail=err, code=status.HTTP_400_BAD_REQUEST)

    return x


def gemini_call(prompt: str, model="gemini-1.5-pro", user=None):
    x = io.StringIO()
    try:
        genai.configure(api_key=ApiKeys.key_for(user, Provider.GEMINI))
        model = genai.GenerativeModel(model)
        response = model.generate_content(prompt)
        for chunk in response:
            x.write(chunk)

    except Exception as err:
        logger.error(err)
        raise APIException(detail=err, code=status.HTTP_400_BAD_REQUEST)

    return x


def claude_call(prompt: str, model="claude-3-5-sonnet-20240620", user=None):
    x = io.StringIO()
    try:
        client = anthropic.Anthropic(api_key=ApiKeys.key_for(user, Provider.ANTHROPIC))
        message = client.messages.create(
            model=model,
            max_tokens=1000,
            temperature=0,
            system="You are a world-class poet. Respond only with short poems.",
            messages=[
                {"role": "assistant", "content": [{"type": "text", "text": prompt}]}
            ],
        )

        x.write(message.content[0].text)
        return x
    except Exception as err:
        logger.error(err)
        raise APIException(err, code=status.HTTP_400_BAD_REQUEST)


def get_reply(prompt, time=0, reply_format="json", gpt_model="gpt-4", user=None):
    """
    Get a reply to a prompt from the model named by `gpt_model`.

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
    - Routes to OpenAI, Claude or Gemini based on the model name.
    """
    time += 1

    for key, call in model_calls:
        if (gpt_model or "").startswith(key):
            x = getattr(thismodule, call)(prompt, gpt_model, user=user)
            break
    else:
        x = official_gpt_call(prompt, gpt_model=settings.DEFAULT_GPT_MODEL, user=user)

    if reply_format == "json":
        x = x.getvalue()

        try:
            # Inside the try: a reply with no braces at all — a refusal, or plain
            # prose — makes index() raise, and that has to come back as the same
            # APIException as any other unparsable reply rather than a 500.
            x = x[x.index("{") : len(x) - (x[::-1].index("}"))]

            js = json.loads(x)
            if not check_json(js):
                raise InvalidJsonFormatException()

            return js

        except InvalidJsonFormatException:
            if time == 5:
                raise Exception(
                    "Max gpt limit is 5 , try again with different prompt !!"
                )

            return get_reply(prompt, time=time, gpt_model=gpt_model, user=user)

        except Exception as exc:
            logger.error(exc)
            logger.debug("Unparsable model reply: %s", x)
            raise APIException(
                detail="There was a problem with the ai model",
                code=status.HTTP_400_BAD_REQUEST,
            )

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
    response = g4f.ChatCompletion.create(
        model="gpt-4",
        messages=[{"content": prompt}],
        stream=True,
    )
    x = io.StringIO()
    for message in response:
        x.write(message)

    return x.getvalue()


def select_from_vision(prompt, images, user=None):
    logger.warning("API CALL IN OFFICIAL GPT vision")

    client = OpenAI(api_key=ApiKeys.key_for(user, Provider.OPENAI))

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"I will send you 3 images, i want you to pick 1 , that is closer"
                    f" on this prompt : {prompt}."
                    f"Answer me with a number from 1 to 3 ",
                },
            ],
        }
    ]

    for x in images:
        dicts = {"type": "image_url", "image_url": {"url": x}}
        messages[0]["content"].append(dicts)

    # gpt-4-vision-preview was retired; gpt-4o reads images natively.
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=300,
    )
    x = response.choices[0].message.content

    x = 0 if "1" in x else 1 if "2" in x else 2

    return x
