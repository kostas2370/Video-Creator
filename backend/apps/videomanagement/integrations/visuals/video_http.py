"""Small HTTP helpers for built-in video providers; no process-global credentials."""

import functools
import logging
import math
import re
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from django.conf import settings
from rest_framework.exceptions import APIException

from apps.apikeysmanagement.models import ApiKeys
from apps.videomanagement.utils.image_inputs import image_data
from .custom import save_video
from .registry import ImageProviderRegistry

logger = logging.getLogger(__name__)
MAX_VIDEO_BYTES = 200 * 1024 * 1024


def guarded(label):
    def decorate(fn):
        @functools.wraps(fn)
        def call(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except APIException:
                raise
            except Exception as exc:
                # Requests errors may embed signed download URLs or credentials.
                logger.warning(
                    "%s video generation failed (%s)", label, type(exc).__name__
                )
                raise APIException(
                    f"{label} could not generate this video. Check your API key, "
                    "provider balance and access, then try again."
                ) from None

        return call

    return decorate


@dataclass(frozen=True)
class VideoRequest:
    """Prepared scene input and authenticated calls shared by video adapters."""

    prompt: str
    directory: str
    seconds: int
    image: str | None = field(repr=False)
    video_format: str
    user: object
    headers: dict = field(repr=False)
    label: str

    @property
    def image_uri(self):
        return f"data:image/jpeg;base64,{self.image}" if self.image else None

    def aspect_ratio(self, *, square=True):
        if self.video_format == "PORTRAIT":
            return "9:16"
        return "1:1" if square and self.video_format == "SQUARE" else "16:9"

    def get(self, url):
        return json_request("GET", url, headers=self.headers)

    def post(self, url, body, *, timeout=60):
        return json_request(
            "POST", url, headers=self.headers, body=body, timeout=timeout
        )

    def wait(self, url, *, completed, pending, field="status"):
        return poll(
            lambda: self.get(url),
            field=field,
            completed=completed,
            pending=pending,
            label=self.label,
        )


def video_provider(
    name,
    *,
    label,
    provider,
    minimum,
    maximum,
    auth_scheme="Bearer",
    auth_header="Authorization",
    extra_headers=None,
    register=True,
):
    """Keep registry handlers uniform while adapters describe only their protocol."""

    def decorate(fn):
        @guarded(label)
        @functools.wraps(fn)
        def generate(
            prompt,
            dir_name,
            style="",
            duration=0,
            reference=None,
            video_format="LANDSCAPE",
            user=None,
            **kwargs,
        ):
            key = key_for(user, provider)
            return fn(
                VideoRequest(
                    prompt=shot_prompt(prompt, style, reference),
                    directory=dir_name,
                    seconds=seconds_for(duration, minimum, maximum),
                    image=image_data(reference),
                    video_format=video_format,
                    user=user,
                    headers={
                        **(extra_headers or {}),
                        auth_header: f"{auth_scheme} {key}".strip(),
                    },
                    label=label,
                )
            )

        if register:
            return ImageProviderRegistry.register(
                name, output_type="VIDEO", supports_reference=True
            )(generate)
        return generate

    return decorate


def key_for(user, provider):
    key = ApiKeys.key_for(user, provider)
    if not key:
        raise APIException(
            f"Add a {provider.label} API key or enable configured service keys."
        )
    return key


def json_request(method, url, *, headers, body=None, timeout=60):
    with requests.request(
        method,
        url,
        headers=headers,
        json=body,
        timeout=(10, timeout),
        allow_redirects=False,
    ) as response:
        if not 200 <= response.status_code < 300:
            raise APIException(
                f"Video provider rejected the request (HTTP {response.status_code}). "
                "Check your key, balance, model access, and prompt."
            )
        payload = response.json()
    if not isinstance(payload, dict):
        raise APIException("Video provider returned an invalid response.")
    return payload


def poll(fetch, *, field="status", completed, pending, label):
    deadline = time.monotonic() + settings.VIDEO_GENERATION_TIMEOUT
    while time.monotonic() < deadline:
        payload = fetch()
        state = payload.get(field)
        if state in completed:
            if payload.get("error"):
                raise APIException(
                    f"{label} generation failed. Try a different prompt."
                )
            return payload
        if state not in pending:
            raise APIException(f"{label} generation failed or was cancelled.")
        time.sleep(settings.VIDEO_POLL_INTERVAL)
    raise APIException(
        f"{label} generation timed out. The provider may still finish and charge "
        "for the request; check its dashboard before retrying."
    )


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,256}", value):
        raise APIException("Video provider returned an invalid job identifier.")
    return value


def api_url(value, host):
    parsed = urlparse(value) if isinstance(value, str) else None
    if (
        not parsed
        or parsed.scheme != "https"
        or parsed.hostname != host
        or parsed.port not in (None, 443)
        or parsed.username
        or parsed.password
    ):
        raise APIException("Video provider returned an invalid API URL.")
    return value


def seconds_for(duration, minimum, maximum):
    value = duration or settings.SILENT_SCENE_SECONDS
    return max(minimum, min(maximum, math.ceil(value)))


def shot_prompt(prompt, style="", reference=None):
    text = f"One continuous shot, no cuts. {prompt}"
    text += (
        " No montage, internal cuts, fade to black, opening fade, or closing transition."
        " Keep the final action and reaction visible until the clip ends."
        " Use only explicitly specified dialogue and natural ambient sounds."
        " No background music or invented speech; the editor supplies the shared soundtrack."
    )
    if style:
        text += f" Visual style: {style}."
    if reference:
        text += " Start from the supplied frame; preserve subjects, clothing, lighting and motion."
    return text


def save_download(url, directory, *, headers=None, auth_host=None):
    # Provider downloads can redirect to signed CDN URLs. Scope credentials to
    # the API host and follow redirects ourselves so custom key headers never leak.
    download_headers = headers or {}
    if download_headers:
        api_url(url, auth_host)
    for _ in range(4):
        parsed = urlparse(url) if isinstance(url, str) else None
        if (
            not parsed
            or parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            raise APIException("Video provider returned an invalid download URL.")
        with requests.get(
            url,
            headers=download_headers,
            stream=True,
            timeout=(10, 120),
            allow_redirects=False,
        ) as response:
            if response.status_code in (301, 302, 303, 307, 308):
                target = urljoin(url, response.headers.get("Location", ""))
                if target == url:
                    raise APIException("Video download returned an invalid redirect.")
                if (urlparse(target).hostname, urlparse(target).port) != (
                    parsed.hostname,
                    parsed.port,
                ):
                    download_headers = {}
                url = target
                continue
            if not 200 <= response.status_code < 300:
                raise APIException("Could not download the generated video.")
            with tempfile.SpooledTemporaryFile(max_size=1024 * 1024) as stream:
                count = 0
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    count += len(chunk)
                    if count > MAX_VIDEO_BYTES:
                        raise APIException(
                            "Generated video exceeds the 200 MB download limit."
                        )
                    stream.write(chunk)
                stream.seek(0)
                return save_stream(stream, directory)
    raise APIException("Video download returned too many redirects.")


def save_stream(stream, directory):
    Path(directory).mkdir(parents=True, exist_ok=True)
    path = str(Path(directory) / f"{uuid.uuid4()}.mp4")
    try:
        save_video(stream, path)
        return path
    except Exception:
        Path(path).unlink(missing_ok=True)
        raise
