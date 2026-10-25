"""Gemini Omni Flash via Interactions REST; reads model-output steps, not SDK aliases."""

import base64
import math
import re
from io import BytesIO
from urllib.parse import urlparse

from apps.apikeysmanagement.models import Provider
from apps.videomanagement.services.usage import record_usage
from apps.videomanagement.utils.timing import video_metadata
from .registry import ImageProviderRegistry
from . import video_http as http

MODEL = "gemini-omni-1.1-flash"
HOST = "generativelanguage.googleapis.com"
BASE = f"https://{HOST}/v1beta"


def video_output(payload):
    for step in payload.get("steps", []):
        if step.get("type") == "model_output":
            for content in step.get("content", []):
                if content.get("type") == "video":
                    return content
    raise http.APIException("Gemini returned no video. Try a different prompt.")


@ImageProviderRegistry.register("gemini-video", output_type="VIDEO")
@http.guarded("Gemini")
def generate_from_gemini_video(
    prompt,
    dir_name,
    style="",
    duration=0,
    reference=None,
    video_format="LANDSCAPE",
    user=None,
    **kwargs,
):
    headers = {"x-goog-api-key": http.key_for(user, Provider.GEMINI)}
    text = http.shot_prompt(prompt, style, reference)
    text += f" Aim for {http.seconds_for(duration, 3, 10)} seconds."
    content = []
    anchor = http.image_data(reference)
    if anchor:
        content.append({"type": "image", "mime_type": "image/jpeg", "data": anchor})
    content.append({"type": "text", "text": text})
    result = http.json_request(
        "POST",
        f"{BASE}/interactions",
        headers=headers,
        timeout=600,
        body={
            "model": MODEL,
            "input": content,
            "background": False,
            "store": False,
            "stream": False,
            "response_format": {
                "type": "video",
                "delivery": "uri",
                "aspect_ratio": "9:16" if video_format == "PORTRAIT" else "16:9",
                "resolution": "720p",
            },
        },
    )
    if result.get("status") != "completed":
        raise http.APIException("Gemini did not complete video generation.")
    output = video_output(result)
    if output.get("uri"):
        uri = output["uri"]
        if uri.startswith("files/"):
            file_id = http.identifier(uri.removeprefix("files/"))
        else:
            http.api_url(uri, HOST)
            match = re.fullmatch(
                r"/v1beta/files/([A-Za-z0-9_-]+)(?::download)?", urlparse(uri).path
            )
            if not match:
                raise http.APIException("Gemini returned an invalid video file.")
            file_id = match.group(1)
        http.poll(
            lambda: http.json_request(
                "GET", f"{BASE}/files/{file_id}", headers=headers
            ),
            field="state",
            completed={"ACTIVE"},
            pending={"PROCESSING"},
            label="Gemini",
        )
        path = http.save_download(
            f"{BASE}/files/{file_id}:download?alt=media",
            dir_name,
            headers=headers,
            auth_host=HOST,
        )
    elif output.get("data"):
        encoded = output["data"]
        if len(encoded) > http.MAX_VIDEO_BYTES * 4 // 3 + 4:
            raise http.APIException(
                "Generated video exceeds the 200 MB download limit."
            )
        path = http.save_stream(
            BytesIO(base64.b64decode(encoded, validate=True)), dir_name
        )
    else:
        raise http.APIException("Gemini returned no downloadable video.")
    # Omni controls clip duration; record observed seconds rather than the prompt's target.
    seconds = math.ceil(video_metadata(path)["duration"])
    record_usage(
        user,
        "video",
        Provider.GEMINI,
        MODEL,
        seconds=seconds,
        usage=result.get("usage"),
    )
    return path
