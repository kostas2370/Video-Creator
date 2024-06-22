import requests
import urllib.request
import uuid
from ..gpt_utils import select_from_vision
from django.conf import settings
from requests import Response
from typing import Union


def build_payload(query: str, start: int = 1, num: int = 1, **params) -> dict:
    payload = {'key': settings.API_KEY,
               'q': query, 'cx': settings.SEARCH_ENGINE_ID,
               'start': start,
               'num': num,
               "searchType": "image",
               'imgSize':'large',
               'safe':'off'
        }

    payload.update(params)

    return payload


def make_request(payload: dict) -> Response:
    response = requests.get('https://www.googleapis.com/customsearch/v1', params = payload)
    if response.status_code != 200:
        raise Exception('Request Failed')
    return response


def download(q: str, amt: int = 1, path: str = '') -> Union[str, None]:
    payload = build_payload(q, num = amt)
    try:
        response = make_request(payload)

    except Exception as exc:
        print(exc)
        return None

    if response.status_code != 200:
        raise Exception("Couldn't find images")

    data = response.json()
    urls = [item['link'] for item in data['items']]

    image_url = data['items'][0]["link"] \
        if len(urls) == 1 or not settings.VISION_SELECTION \
        else \
        data['items'][select_from_vision(q, urls)]['link']

    filename = str(uuid.uuid4())
    filetype = ".png" if 'png' in image_url else '.gif' if 'gif' in image_url else '.jpg'
    urllib.request.urlretrieve(image_url, f"{path}\\{filename}{filetype}")

    return f"{path}\\{filename}{filetype}"
