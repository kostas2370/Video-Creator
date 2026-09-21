import logging
import os
import urllib.request
import uuid
from typing import Union

import requests
from django.conf import settings
from requests import Response

from apps.apikeysmanagement.models import ApiKeys, Provider

from ..llm import select_from_vision

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

    if response.status_code != 200:
        raise Exception("Couldn't find images")

    data = response.json()
    urls = [item["link"] for item in data["items"]]

    image_url = (
        data["items"][0]["link"]
        if len(urls) == 1 or not settings.VISION_SELECTION
        else data["items"][select_from_vision(q, urls, user=user)]["link"]
    )

    filetype = (
        ".png" if "png" in image_url else ".gif" if "gif" in image_url else ".jpg"
    )
    saved = os.path.join(path, f"{uuid.uuid4()}{filetype}")
    urllib.request.urlretrieve(image_url, saved)

    return saved


def download_image_from_google(
    q: str, path: str, amt: int = 1, user=None, *args, **kwargs
) -> str:
    """
    Download images from Google using a downloader.

    Parameters:
    -----------
    q : str
        The search query for images.
    path : str
        The directory path where the downloaded images will be saved.
    amt : int, optional
        The number of images to download. Default is 1.
    *args, **kwargs : additional arguments and keyword arguments
        Additional arguments and keyword arguments to pass to the downloader.

    Returns:
    --------
    str
        The path to the downloaded image.

    Notes:
    ------
    - This function uses a downloader to download images from Google based on the provided search query.
    - The downloaded image is saved in the specified directory path.
    - The number of images to download can be specified using the 'amt' parameter.
    - Additional arguments and keyword arguments can be passed to the downloader.
    """
    try:
        logger.info("Downloading image from google")
        return download(q=q, path=path, amt=amt, user=user)

    except Exception as exc:
        logger.error(f"Error downloading image with query {q} Error {exc}")
