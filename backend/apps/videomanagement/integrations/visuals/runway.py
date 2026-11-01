"""Runway Gen-4.5 text/image-to-video with bounded task polling."""

from apps.videomanagement.integrations.visuals.registry import ImageProviderRegistry


from apps.apikeysmanagement.models import Provider
from apps.usage.services import record_usage
from . import video_http as http

MODEL = "gen4.5"
BASE = "https://api.dev.runwayml.com/v1"
RATIOS = {"16:9": "1280:720", "9:16": "720:1280", "1:1": "960:960"}


@ImageProviderRegistry.register("runway", output_type="VIDEO", supports_reference=True)
class RunwayProvider(http.DurationVideoProvider):
    PROVIDER = Provider.RUNWAY
    MODEL = MODEL
    MINIMUM = 2
    MAXIMUM = 10

    @staticmethod
    @http.video_provider(
        "runway",
        label="Runway",
        provider=Provider.RUNWAY,
        minimum=MINIMUM,
        maximum=MAXIMUM,
        extra_headers={"X-Runway-Version": "2024-11-06"},
        register=False,
    )
    def generate(request):
        if len(request.prompt.encode("utf-16-le")) // 2 > 1000:
            raise http.APIException(
                "Runway allows 1,000 characters including shared continuity and shot "
                "instructions. Shorten the visual prompt or continuity description."
            )
        # Text-to-video supports portrait/landscape; square is cropped by the renderer.
        body = {
            "model": MODEL,
            "promptText": request.prompt,
            "duration": request.seconds,
            "ratio": RATIOS[request.aspect_ratio(square=bool(request.image))],
        }
        endpoint = "text_to_video"
        if request.image_uri:
            endpoint = "image_to_video"
            body["promptImage"] = request.image_uri
        job = request.post(f"{BASE}/{endpoint}", body)
        job_id = http.identifier(job.get("id"))
        result = request.wait(
            f"{BASE}/tasks/{job_id}",
            completed={"SUCCEEDED"},
            pending={"PENDING", "THROTTLED", "RUNNING"},
        )
        record_usage(
            request.user, "video", Provider.RUNWAY, MODEL, seconds=request.seconds
        )
        return http.save_download(result["output"][0], request.directory)


generate_from_runway = RunwayProvider.generate
