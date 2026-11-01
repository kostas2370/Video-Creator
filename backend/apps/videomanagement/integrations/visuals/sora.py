from rest_framework.exceptions import APIException

from apps.usage.pricing import estimate_line
from apps.videomanagement.integrations.base import ImageProvider
from apps.videomanagement.integrations.visuals.registry import ImageProviderRegistry


SORA_RETIRED_MESSAGE = "Sora is no longer available. Choose Kling, Runway or Gemini video to generate new clips."


@ImageProviderRegistry.register("sora", output_type="VIDEO", supports_reference=True)
class SoraProvider(ImageProvider):
    @staticmethod
    def generate(*args, **kwargs):
        raise APIException(SORA_RETIRED_MESSAGE)

    @staticmethod
    def calculate(request):
        line = estimate_line(
            "Animation",
            "video",
            "sora",
            "sora-2",
            {"requests": request.count},
            custom=True,
        )
        line["note"] = SORA_RETIRED_MESSAGE
        return line
