from apps.videomanagement.integrations.base import ImageProvider
from apps.usage.pricing import image_estimate
import logging
import os
import urllib.request
import uuid

import requests

from apps.apikeysmanagement.models import ApiKeys, Provider
from apps.videomanagement.integrations.visuals.registry import ImageProviderRegistry
from apps.usage.services import record_usage
from apps.videomanagement.utils.prompt_utils import format_image_prompt

logger = logging.getLogger(__name__)


@ImageProviderRegistry.register("stable-diffusion")
class StableDiffusionProvider(ImageProvider):
    @staticmethod
    def generate(
        prompt: str, dir_name: str, title: str = "", user=None, *args, **kwargs
    ):
        url = "https://stablediffusionapi.com/api/v3/text2img"

        diffusion_key = ApiKeys.key_for(user, Provider.STABLE_DIFFUSION)
        if not diffusion_key:
            logger.error("Tried to call diffusion but no api key")
            return

        logger.warning("Api call in diffusion")
        payload = {
            "key": diffusion_key,
            "prompt": format_image_prompt(title=title, image_description=prompt),
            "negative_prompt": None,
            "width": "1024",
            "height": "1024",
            "samples": "1",
            "num_inference_steps": "20",
            "guidance_scale": 7.5,
        }

        response = requests.post(url, json=payload)
        body = response.json()
        output = body.get("output") or []

        if not output:
            logger.error("Diffusion returned no image: %s", body.get("status"))
            return

        saved = os.path.join(dir_name, f"{uuid.uuid4()}.png")
        record_usage(user, "images", Provider.STABLE_DIFFUSION, images=1)
        urllib.request.urlretrieve(output[0], saved)
        return saved

    @staticmethod
    def calculate(request):
        return image_estimate(request.count, Provider.STABLE_DIFFUSION)
