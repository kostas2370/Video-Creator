import requests
import urllib.request
import uuid
from django.conf import settings


def build_payload(query, start=1, num=1, **params):
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


def make_request(payload):
    response = requests.get('https://www.googleapis.com/customsearch/v1', params = payload)
    if response.status_code != 200:
        raise Exception('Request Failed')
    return response


def download(q, amt=1, path=''):
    payload = build_payload(q, num = amt)
    try:
        response = make_request(payload)
    except:
        return None

    if response.status_code != 200:
        raise Exception("Couldn't find images")

    data = response.json()
    image_url = data['items'][0]["link"]
    print(image_url)

    filename = str(uuid.uuid4())
    filetype = ".png" if 'png' in image_url else '.gif' if 'gif' in image_url else '.jpg'
    urllib.request.urlretrieve(image_url, f"{path}\\{filename}{filetype}")

    return f"{path}\\{filename}{filetype}"
