import logging
import os
import urllib.request
import uuid

from apps.apikeysmanagement.key_health import provider_request
from apps.apikeysmanagement.models import ApiKeys, Provider
from apps.usage.pricing import image_estimate
from apps.usage.services import record_usage
from apps.videomanagement.integrations.base import ImageProvider
from apps.videomanagement.integrations.visuals.registry import ImageProviderRegistry
from apps.videomanagement.prompts.visuals import format_image_prompt

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
        response = provider_request(
            "POST",
            "https://api.mymidjourney.ai/api/v1/midjourney/imagine",
            headers=headers,
            json=payload,
            user=user,
            provider=Provider.MIDJOURNEY,
        )
        response = response.json()

        if not response.get("success"):
            logger.error("Failed to generate image with midjourney: %s", response)
            return

        job_id = response["messageId"]
        response = provider_request(
            "GET",
            f"https://api.mymidjourney.ai/api/v1/midjourney/message/{job_id}",
            headers=headers,
            user=user,
            provider=Provider.MIDJOURNEY,
        )
        image = response.json().get("uri")

        if not image:
            logger.error("Midjourney returned no image for %s", job_id)
            return

        saved = os.path.join(dir_name, f"{uuid.uuid4()}.png")
        record_usage(user, "images", Provider.MIDJOURNEY, images=1)
        urllib.request.urlretrieve(image, saved)
        return saved

    @staticmethod
    def calculate(request):
        return image_estimate(request.count, Provider.MIDJOURNEY)
