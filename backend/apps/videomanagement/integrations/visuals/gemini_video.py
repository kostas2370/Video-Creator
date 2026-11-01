"""Gemini Omni Flash via Interactions REST; reads model-output steps, not SDK aliases."""

import base64
import math
import re
from io import BytesIO
from urllib.parse import urlparse

from apps.apikeysmanagement.models import Provider
from apps.usage.services import record_usage
from apps.videomanagement.utils.timing import video_metadata
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


@http.video_provider(
    "gemini-video",
    label="Gemini",
    provider=Provider.GEMINI,
    minimum=3,
    maximum=10,
    auth_scheme="",
    auth_header="x-goog-api-key",
)
def generate_from_gemini_video(request):
    content = []
    if request.image:
        content.append(
            {"type": "image", "mime_type": "image/jpeg", "data": request.image}
        )
    content.append(
        {"type": "text", "text": f"{request.prompt} Aim for {request.seconds} seconds."}
    )
    result = request.post(
        f"{BASE}/interactions",
        {
            "model": MODEL,
            "input": content,
            "background": False,
            # URI delivery requires a stored interaction so the file can be fetched.
            "store": True,
            "stream": False,
            "response_format": {
                "type": "video",
                "delivery": "uri",
                "aspect_ratio": request.aspect_ratio(square=False),
                "resolution": "720p",
            },
        },
        timeout=600,
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
        request.wait(
            f"{BASE}/files/{file_id}",
            field="state",
            completed={"ACTIVE"},
            pending={"PROCESSING"},
        )
        path = http.save_download(
            f"{BASE}/files/{file_id}:download?alt=media",
            request.directory,
            headers=request.headers,
            auth_host=HOST,
        )
    elif output.get("data"):
        encoded = output["data"]
        if len(encoded) > http.MAX_VIDEO_BYTES * 4 // 3 + 4:
            raise http.APIException(
                "Generated video exceeds the 200 MB download limit."
            )
        path = http.save_stream(
            BytesIO(base64.b64decode(encoded, validate=True)), request.directory
        )
    else:
        raise http.APIException("Gemini returned no downloadable video.")
    # Omni controls clip duration; record observed seconds rather than the prompt's target.
    seconds = math.ceil(video_metadata(path)["duration"])
    record_usage(
        request.user,
        "video",
        Provider.GEMINI,
        MODEL,
        seconds=seconds,
        usage=result.get("usage"),
    )
    return path
