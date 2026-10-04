import logging
import os
import shutil
import subprocess
import tempfile
import uuid
from contextlib import ExitStack
from urllib.parse import urlparse

import requests
from PIL import Image
from moviepy.config import get_setting
from moviepy.editor import VideoFileClip
from rest_framework.exceptions import NotFound, ValidationError

from apps.apikeysmanagement.models import UserCustomVisualProvider, VisualOutputType

from .registry import ImageProviderRegistry

logger = logging.getLogger(__name__)
DEFAULT_TIMEOUT = 30
VIDEO_TIMEOUT = 300


def media_url(payload, output_type="IMAGE"):
    """Accept direct URLs or the first entry in an OpenAI-style data list."""
    if not isinstance(payload, dict):
        raise ValueError("The provider returned an invalid media response.")
    field = "video_url" if output_type == VisualOutputType.VIDEO else "image_url"
    url = payload.get("url") or payload.get(field)
    if not url:
        data = payload.get("data")
        if isinstance(data, list) and data and isinstance(data[0], dict):
            url = data[0].get("url") or data[0].get(field)
    if not isinstance(url, str):
        raise ValueError("The provider returned no media URL.")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("The media URL must use HTTP or HTTPS.")
    return url


def save_video(downloaded, path):
    """Validate a real clip and normalize its container/codecs for the renderer."""
    with tempfile.TemporaryDirectory() as directory:
        source = os.path.join(directory, "source.mp4")
        with open(source, "wb") as file:
            shutil.copyfileobj(downloaded, file)
        with VideoFileClip(source, audio=False) as clip:
            if not clip.duration or clip.duration <= 0 or not clip.fps:
                raise ValueError("The provider returned an invalid video.")
            clip.get_frame(0)
        subprocess.run(
            [
                get_setting("FFMPEG_BINARY"),
                "-nostdin",
                "-y",
                "-i",
                source,
                "-map",
                "0:v:0",
                "-map",
                "0:a?",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-vf",
                "pad=ceil(iw/2)*2:ceil(ih/2)*2",
                "-c:a",
                "aac",
                "-movflags",
                "+faststart",
                path,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=VIDEO_TIMEOUT,
        )


@ImageProviderRegistry.register_fallback()
def generate_from_custom_provider(
    prompt: str,
    dir_name: str,
    user=None,
    provider_name: str = None,
    **kwargs,
):
    """Retrieve a synchronous custom visual and return a local PNG or MP4 path."""
    if (
        user is None
        or not getattr(user, "is_authenticated", False)
        or not provider_name
    ):
        raise NotFound("Custom visual provider is unavailable.")
    try:
        provider = UserCustomVisualProvider.objects.get(user=user, name=provider_name)
    except UserCustomVisualProvider.DoesNotExist:
        raise NotFound("Custom visual provider is unavailable.")
    if provider.output_type not in VisualOutputType.values:
        raise ValidationError("Unsupported visual output type.")

    is_video = provider.output_type == VisualOutputType.VIDEO
    timeout = VIDEO_TIMEOUT if is_video else DEFAULT_TIMEOUT
    headers, auth = provider.get_auth_headers()
    headers["Accept"] = f"{'video' if is_video else 'image'}/*, application/json"
    saved_path = None
    try:
        with ExitStack() as stack:
            response = stack.enter_context(
                requests.post(
                    provider.endpoint_url,
                    json=provider.request_payload({provider.prompt_field_name: prompt}),
                    headers=headers,
                    auth=auth,
                    timeout=timeout,
                    stream=True,
                    allow_redirects=False,
                )
            )
            response.raise_for_status()
            content_type = (
                response.headers.get("Content-Type", "")
                .split(";", 1)[0]
                .strip()
                .lower()
            )
            if content_type == "application/json" or content_type.endswith("+json"):
                # A media URL may use a different host or its own signed credential.
                # Keep the synthesis credential on its configured endpoint only.
                response = stack.enter_context(
                    requests.get(
                        media_url(response.json(), provider.output_type),
                        timeout=timeout,
                        stream=True,
                    )
                )
                response.raise_for_status()

            with tempfile.SpooledTemporaryFile(max_size=1024 * 1024) as downloaded:
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        downloaded.write(chunk)
                downloaded.seek(0)
                if is_video:
                    os.makedirs(dir_name, exist_ok=True)
                    saved_path = os.path.join(dir_name, f"{uuid.uuid4()}.mp4")
                    save_video(downloaded, saved_path)
                    return saved_path
                with Image.open(downloaded) as image:
                    image.load()
                    os.makedirs(dir_name, exist_ok=True)
                    saved_path = os.path.join(dir_name, f"{uuid.uuid4()}.png")
                    # Normalize supported source formats into the renderer's PNG format.
                    mode = (
                        "RGBA"
                        if "A" in image.getbands() or "transparency" in image.info
                        else "RGB"
                    )
                    with image.convert(mode) as normalized:
                        normalized.save(saved_path, format="PNG")
        return saved_path
    except Exception:
        if saved_path and os.path.exists(saved_path):
            os.remove(saved_path)
        # Response bodies and request URLs can contain credentials. Do not log them.
        logger.error(
            "Could not retrieve a visual from custom provider %s", provider.name
        )
        return None
