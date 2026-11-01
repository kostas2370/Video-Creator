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


@ImageProviderRegistry.register("midjourney")
class MidjourneyProvider(ImageProvider):
    @staticmethod
    def generate(
        prompt: str, dir_name: str, title: str = "", user=None, *args, **kwargs
    ):
        midjourney_key = ApiKeys.key_for(user, Provider.MIDJOURNEY)
        if not midjourney_key:
            logger.error("Tried to call MIDJOURNEY but no api key")
            return

        logger.warning("Api call in midjourney")
        payload = {"prompt": format_image_prompt(title, prompt)}
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
        record_usage(user, "images", Provider.MIDJOURNEY, images=1)
        urllib.request.urlretrieve(image, saved)
        return saved

    @staticmethod
    def calculate(request):
        return image_estimate(request.count, Provider.MIDJOURNEY)
