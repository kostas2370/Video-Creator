from apps.videomanagement.integrations.base import ImageProvider
from apps.usage.pricing import estimate_line, image_estimate
import logging
import os
import shutil
import tempfile
import uuid
from contextlib import ExitStack
from urllib.parse import urlparse

import requests
from PIL import Image
from rest_framework.exceptions import NotFound, ValidationError

from apps.apikeysmanagement.models import UserCustomVisualProvider, VisualOutputType
from apps.common.media import run_ffmpeg
from apps.videomanagement.integrations.visuals.registry import ImageProviderRegistry
from apps.usage.services import record_usage
from apps.videomanagement.utils.timing import video_metadata

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
        video_metadata(source)
        run_ffmpeg(
            [
                "-xerror",
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
            timeout=VIDEO_TIMEOUT,
        )


@ImageProviderRegistry.register_fallback()
class CustomImageProvider(ImageProvider):
    @staticmethod
    def generate(
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
            provider = UserCustomVisualProvider.objects.get(
                user=user, name=provider_name
            )
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
                        json=provider.request_payload(
                            {provider.prompt_field_name: prompt}
                        ),
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
                payload = None
                download_url = None
                if content_type == "application/json" or content_type.endswith("+json"):
                    payload = response.json()
                    download_url = media_url(payload, provider.output_type)

                # Generation has completed upstream, even if local processing later fails.
                record_usage(
                    user,
                    "video" if is_video else "images",
                    provider_name,
                    usage=payload.get("usage") if payload else None,
                    images=0 if is_video else 1,
                    custom=True,
                )
                if download_url:
                    # Keep synthesis credentials on the configured endpoint only.
                    response = stack.enter_context(
                        requests.get(download_url, timeout=timeout, stream=True)
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

    @staticmethod
    def calculate(request):
        if request.output_type == "VIDEO":
            return estimate_line(
                "Animation",
                "video",
                request.provider_name,
                "",
                {"requests": request.count},
                custom=True,
            )
        return image_estimate(request.count, request.provider_name, custom=True)
