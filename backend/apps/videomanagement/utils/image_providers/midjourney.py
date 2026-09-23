import logging
import os
import urllib.request
import uuid

import requests

from apps.apikeysmanagement.models import ApiKeys, Provider

from ..prompt_utils import format_dalle_prompt

logger = logging.getLogger(__name__)


def generate_from_midjourney(
    prompt: str, dir_name: str, title: str = "", user=None, *args, **kwargs
):
    """
    Generate an image using the Midjourney API.

    Parameters:
    -----------
    prompt : str
        The prompt for generating the image.
    dir_name : str
        The directory path where the generated image will be saved.
    title : str, optional
        The title for the image. Default is an empty string.


    Returns:
    --------
    str
        The path to the generated image file.

    Notes:
    ------
    - This function uses the Midjourney API to generate an image based on the provided prompt.
    - The generated image is saved in the specified directory path.
    - The filename of the generated image is a UUID followed by '.png'.
    """
    midjourney_key = ApiKeys.key_for(user, Provider.MIDJOURNEY)
    if not midjourney_key:
        logger.error("Tried to call MIDJOURNEY but no api key")
        return

    logger.warning("Api call in midjourney")
    payload = {"prompt": format_dalle_prompt(title, prompt)}
    headers = {"Authorization": f"Bearer {midjourney_key}"}
    response = requests.post(
        "https://api.mymidjourney.ai/api/v1/midjourney/imagine",
        headers=headers,
        json=payload,
    ).json()

    if not response.get("success"):
        logger.error("Failed to generate image with midjourney: %s", response)
        return

    image = (
        requests.get(
            f"https://api.mymidjourney.ai/api/v1/midjourney/message/{response['messageId']}",
            headers=headers,
        )
        .json()
        .get("uri")
    )

    if not image:
        logger.error("Midjourney returned no image for %s", response["messageId"])
        return

    saved = os.path.join(dir_name, f"{uuid.uuid4()}.png")
    urllib.request.urlretrieve(image, saved)
    return saved
