"""Kling O3 reference-to-video through fal's queued API."""

from apps.apikeysmanagement.models import Provider
from apps.usage.services import record_usage
from . import video_http as http

MODEL = "fal-ai/kling-video/o3/pro/reference-to-video"


@http.video_provider(
    "kling",
    label="Kling",
    provider=Provider.FAL,
    minimum=3,
    maximum=15,
    auth_scheme="Key",
)
def generate_from_kling(request):
    body = {
        "prompt": request.prompt,
        "duration": str(request.seconds),
        "aspect_ratio": request.aspect_ratio(),
        "generate_audio": True,
    }
    if request.image_uri:
        body["start_image_url"] = request.image_uri
    job = request.post(f"https://queue.fal.run/{MODEL}", body)
    status_url = http.api_url(job.get("status_url"), "queue.fal.run")
    result_url = http.api_url(job.get("response_url"), "queue.fal.run")
    request.wait(
        status_url,
        completed={"COMPLETED"},
        pending={"IN_QUEUE", "IN_PROGRESS"},
    )
    result = request.get(result_url)
    if result.get("error"):
        raise http.APIException("Kling generation failed. Try a different prompt.")
    record_usage(request.user, "video", Provider.FAL, MODEL, seconds=request.seconds)
    return http.save_download(result["video"]["url"], request.directory)
