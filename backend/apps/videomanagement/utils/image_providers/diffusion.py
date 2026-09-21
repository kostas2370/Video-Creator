import json
import logging
import os
import urllib.request
import uuid

import requests

from apps.apikeysmanagement.models import ApiKeys, Provider

from ..prompt_utils import format_dalle_prompt

logger = logging.getLogger(__name__)


def generate_from_diffusion(
    prompt: str, dir_name: str, title: str = "", user=None, *args, **kwargs
):
    """
    Generate an image using the Diffusion model.

    Parameters:
    -----------
    prompt : str
        The prompt for generating the image.
    dir_name : str
        The directory path where the generated image will be saved.
    title : str, optional
        The title for the image. Default is an empty string.
    *args, **kwargs : additional arguments and keyword arguments
        Additional arguments and keyword arguments to pass to the diffusion model API.

    Returns:
    --------
    str
        The path to the generated image file.

    Notes:
    ------
    - This function uses the Diffusion model API to generate an image based on the provided prompt.
    - The generated image is saved in the specified directory path.
    - The filename of the generated image is a UUID followed by '.png'.
    """

    url = "https://stablediffusionapi.com/api/v3/text2img"

    diffusion_key = ApiKeys.key_for(user, Provider.STABLE_DIFFUSION)
    if not diffusion_key:
        logger.error("Tried to call diffusion but no api key")
        return

    logger.warning("Api call in diffusion")
    payload = json.dumps(
        {
            "key": diffusion_key,
            "prompt": format_dalle_prompt(title=title, image_description=prompt),
            "negative_prompt": None,
            "width": "1024",
            "height": "1024",
            "samples": "1",
            "num_inference_steps": "20",
            "guidance_scale": 7.5,
        }
    )

    headers = {"Content-Type": "application/json"}

    response = requests.post(url, headers=headers, data=payload)
    image = response.json()["output"][0]
    saved = os.path.join(dir_name, f"{uuid.uuid4()}.png")
    urllib.request.urlretrieve(image, saved)
    return saved
