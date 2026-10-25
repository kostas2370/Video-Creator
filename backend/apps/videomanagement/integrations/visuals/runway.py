"""Runway Gen-4.5 text/image-to-video with bounded task polling."""

from apps.apikeysmanagement.models import Provider
from apps.videomanagement.services.usage import record_usage
from .registry import ImageProviderRegistry
from . import video_http as http

MODEL = "gen4.5"
BASE = "https://api.dev.runwayml.com/v1"


@ImageProviderRegistry.register("runway", output_type="VIDEO")
@http.guarded("Runway")
def generate_from_runway(
    prompt,
    dir_name,
    style="",
    duration=0,
    reference=None,
    video_format="LANDSCAPE",
    user=None,
    **kwargs,
):
    headers = {
        "Authorization": f"Bearer {http.key_for(user, Provider.RUNWAY)}",
        "X-Runway-Version": "2024-11-06",
    }
    text = http.shot_prompt(prompt, style, reference)
    if len(text.encode("utf-16-le")) // 2 > 1000:
        raise http.APIException(
            "Runway allows 1,000 characters including shared continuity and shot "
            "instructions. Shorten the visual prompt or continuity description."
        )
    seconds = http.seconds_for(duration, 2, 10)
    anchor = http.image_data(reference)
    # Text-to-video supports portrait/landscape; square is cropped by Viddie's renderer.
    ratio = "720:1280" if video_format == "PORTRAIT" else "1280:720"
    if video_format == "SQUARE" and anchor:
        ratio = "960:960"
    body = {"model": MODEL, "promptText": text, "ratio": ratio, "duration": seconds}
    endpoint = "text_to_video"
    if anchor:
        endpoint = "image_to_video"
        body["promptImage"] = f"data:image/jpeg;base64,{anchor}"
    job = http.json_request("POST", f"{BASE}/{endpoint}", headers=headers, body=body)
    job_id = http.identifier(job.get("id"))
    result = http.poll(
        lambda: http.json_request("GET", f"{BASE}/tasks/{job_id}", headers=headers),
        completed={"SUCCEEDED"},
        pending={"PENDING", "THROTTLED", "RUNNING"},
        label="Runway",
    )
    record_usage(user, "video", Provider.RUNWAY, MODEL, seconds=seconds)
    return http.save_download(result["output"][0], dir_name)
