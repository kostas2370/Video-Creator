from apps.videomanagement.integrations.base import ImageProvider
from apps.usage.pricing import image_estimate
import logging
import os
import urllib.request
import uuid
from typing import Union
from urllib.parse import urlparse

import requests
from django.conf import settings
from requests import Response

from apps.apikeysmanagement.models import ApiKeys, Provider
from apps.videomanagement.integrations.llm import select_from_vision
from apps.videomanagement.integrations.visuals.registry import ImageProviderRegistry

logger = logging.getLogger(__name__)


def build_payload(
    query: str, start: int = 1, num: int = 1, user=None, **params
) -> dict:
    key = ApiKeys.key_for(user, Provider.GOOGLE_SEARCH)
    if not key:
        raise Exception("Google api key is missing")

    payload = {
        "key": key,
        "q": query,
        "cx": ApiKeys.key_for(user, Provider.GOOGLE_SEARCH_ENGINE_ID),
        "start": start,
        "num": num,
        "searchType": "image",
        "imgSize": "large",
        "safe": "off",
    }

    payload.update(params)

    return payload


def make_request(payload: dict) -> Response:
    response = requests.get(
        "https://www.googleapis.com/customsearch/v1", params=payload
    )
    if response.status_code != 200:
        raise Exception("Request Failed")
    return response


def download(q: str, amt: int = 1, path: str = "", user=None) -> Union[str, None]:
    payload = build_payload(q, num=amt, user=user)
    try:
        response = make_request(payload)

    except Exception as exc:
        logger.error(exc)
        return None

    items = response.json().get("items") or []
    if not items:
        logger.error("Google found no images for %r", q)
        return None

    urls = [item["link"] for item in items]

    image_url = (
        urls[0]
        if len(urls) == 1 or not settings.VISION_SELECTION
        else urls[select_from_vision(q, urls, user=user)]
    )

    extension = os.path.splitext(urlparse(image_url).path)[1].lower()
    filetype = extension if extension in {".png", ".gif", ".jpg", ".jpeg"} else ".jpg"
    saved = os.path.join(path, f"{uuid.uuid4()}{filetype}")
    urllib.request.urlretrieve(image_url, saved)

    return saved


@ImageProviderRegistry.register("google", mode="WEB")
class GoogleImageProvider(ImageProvider):
    @staticmethod
    def generate(q: str, path: str, amt: int = 1, user=None, *args, **kwargs) -> str:
        try:
            logger.info("Downloading image from google")
            return download(q=q, path=path, amt=amt, user=user)

        except Exception as exc:
            logger.error(f"Error downloading image with query {q} Error {exc}")
            return None

    @staticmethod
    def calculate(request):
        return image_estimate(request.count, "google", custom=True)
