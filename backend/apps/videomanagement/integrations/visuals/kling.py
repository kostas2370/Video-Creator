"""Kling O3 reference-to-video through fal's queued API."""

from apps.apikeysmanagement.models import Provider
from apps.videomanagement.services.usage import record_usage
from .registry import ImageProviderRegistry
from . import video_http as http

MODEL = "fal-ai/kling-video/o3/pro/reference-to-video"


@ImageProviderRegistry.register("kling", output_type="VIDEO")
@http.guarded("Kling")
def generate_from_kling(
    prompt,
    dir_name,
    style="",
    duration=0,
    reference=None,
    video_format="LANDSCAPE",
    user=None,
    **kwargs,
):
    headers = {"Authorization": f"Key {http.key_for(user, Provider.FAL)}"}
    seconds = http.seconds_for(duration, 3, 15)
    body = {
        "prompt": http.shot_prompt(prompt, style, reference),
        "duration": str(seconds),
        "aspect_ratio": {"PORTRAIT": "9:16", "SQUARE": "1:1"}.get(video_format, "16:9"),
        "generate_audio": True,
    }
    anchor = http.image_data(reference)
    if anchor:
        body["start_image_url"] = f"data:image/jpeg;base64,{anchor}"
    job = http.json_request(
        "POST", f"https://queue.fal.run/{MODEL}", headers=headers, body=body
    )
    status_url = http.api_url(job.get("status_url"), "queue.fal.run")
    result_url = http.api_url(job.get("response_url"), "queue.fal.run")
    http.poll(
        lambda: http.json_request("GET", status_url, headers=headers),
        completed={"COMPLETED"},
        pending={"IN_QUEUE", "IN_PROGRESS"},
        label="Kling",
    )
    result = http.json_request("GET", result_url, headers=headers)
    if result.get("error"):
        raise http.APIException("Kling generation failed. Try a different prompt.")
    record_usage(user, "video", Provider.FAL, MODEL, seconds=seconds)
    return http.save_download(result["video"]["url"], dir_name)
