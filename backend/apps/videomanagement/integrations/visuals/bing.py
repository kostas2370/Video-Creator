from apps.videomanagement.integrations.base import ImageProvider
from apps.usage.pricing import image_estimate
import logging
from typing import Union

from apps.videomanagement.integrations.visuals.registry import ImageProviderRegistry
from vendor.bing_image_downloader import downloader

logger = logging.getLogger(__name__)


@ImageProviderRegistry.register("bing", mode="WEB")
class BingImageProvider(ImageProvider):
    @staticmethod
    def generate(
        query: str, path: str, amount: int = 1, *args, **kwargs
    ) -> Union[str, None]:
        try:
            logger.info("Downloading image from bing")
            return downloader.download(
                query=f"{query}",
                limit=amount,
                output_dir=path,
                adult_filter_off=True,
                force_replace=False,
                timeout=60,
                filter="photo",
            )[0]

        except Exception as exc:
            logger.error(f"Error downloading image with query {query} Error {exc}")
            return None

    @staticmethod
    def calculate(request):
        return image_estimate(request.count, "bing", custom=True)
