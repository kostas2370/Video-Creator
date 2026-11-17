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
from apps.usage.pricing import estimate_line
from apps.videomanagement.integrations.base import ImageProvider
from apps.videomanagement.prompts.visuals import audio_direction
from apps.videomanagement.utils.image_inputs import image_data

from .errors import VideoProviderError
from .custom import save_video
from .registry import ImageProviderRegistry

logger = logging.getLogger(__name__)
MAX_VIDEO_BYTES = 200 * 1024 * 1024


class DurationVideoProvider(ImageProvider):
    @classmethod
    def calculate(cls, request):
        durations = request.durations or (None,) * request.count
        return estimate_line(
            "Animation",
            "video",
            cls.PROVIDER,
            cls.MODEL,
            {
                "seconds": sum(
                    seconds_for(value, cls.MINIMUM, cls.MAXIMUM) for value in durations
                ),
                "requests": len(durations),
            },
        )


def guarded(label):
    def decorate(fn):
        @functools.wraps(fn)
        def call(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except VideoProviderError as exc:
                raise VideoProviderError(f"{label}: {exc}") from None
            except APIException:
                raise
            except requests.Timeout:
                raise VideoProviderError(
                    f"{label} request timed out. Check the provider dashboard before retrying; generation may still finish and incur charges."
                ) from None
            except requests.ConnectionError:
                raise VideoProviderError(
                    f"Could not connect to {label}. Check connectivity and try again later."
                ) from None
            except Exception as exc:
                # Requests errors may embed signed download URLs or credentials.
                reference = uuid.uuid4().hex[:12]
                logger.warning(
                    "%s video generation failed (%s). Reference: %s",
                    label,
                    type(exc).__name__,
                    reference,
                )
                raise VideoProviderError(
                    f"{label} could not complete video generation. The cause could not "
                    f"be determined. Check the worker logs before retrying. Reference: {reference}."
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
    audio_mode: str = "AMBIENT"

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
            audio_mode = kwargs.get("audio_mode", "AMBIENT")
            return fn(
                VideoRequest(
                    prompt=shot_prompt(
                        prompt,
                        style,
                        reference,
                        audio_mode=audio_mode,
                    ),
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
                    audio_mode=audio_mode,
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
        raise VideoProviderError(
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
            reference = uuid.uuid4().hex[:12]
            message = f"{provider_error(response)} Reference: {reference}."
            logger.warning("Video provider request failed: %s", message)
            raise VideoProviderError(message)
        try:
            payload = response.json()
        except ValueError:
            raise VideoProviderError(
                "Video provider returned an unreadable response. Check its dashboard before retrying."
            ) from None
    if not isinstance(payload, dict):
        raise VideoProviderError("Video provider returned an invalid response.")
    return payload


# Only these codes and application-authored hints can reach logs or the UI.
ERROR_HINTS = {
    "INVALID_ARGUMENT": "Check the video request parameters and input image before retrying.",
    "INVALID_REQUEST": "Check the video request parameters and input image before retrying.",
    "FAILED_PRECONDITION": "Check billing and eligibility for the API key's project before retrying.",
    "PAYMENT_REQUIRED": "Restore credits on the API key's provider project before retrying.",
    "UNAUTHENTICATED": "Check the configured provider API key before retrying.",
    "PERMISSION_DENIED": "Check the API key's permissions and model access before retrying.",
    "RESOURCE_EXHAUSTED": "Check the provider project's quota, rate limits and balance before retrying.",
    "NOT_FOUND": "Check that the configured model is available to this API key.",
    "CONTENT_BLOCKED": "The provider's safety filters blocked the prompt or reference image. Edit the shot description or replace the starting frame before retrying.",
    "RECITATION": "The provider blocked generation because of copyright or recitation restrictions. Change the shot description or reference image before retrying.",
    "LANGUAGE": "The provider rejected an unsupported language. Change the shot description to a supported language before retrying.",
    "SPII": "The provider blocked generation because of sensitive personal information. Remove personal details or replace the reference image before retrying.",
    "INTERNAL": "The provider had an internal error. Try again later.",
    "UNAVAILABLE": "The provider is temporarily unavailable. Try again later.",
    "DEADLINE_EXCEEDED": "The provider timed out. Check its dashboard before retrying; generation may still finish and incur charges.",
}
ERROR_ALIASES = {
    "INVALID_REQUEST_ERROR": "INVALID_REQUEST",
    "BAD_REQUEST": "INVALID_REQUEST",
    "AUTHENTICATION": "UNAUTHENTICATED",
    "AUTHENTICATION_ERROR": "UNAUTHENTICATED",
    "RATE_LIMIT": "RESOURCE_EXHAUSTED",
    "RATE_LIMIT_ERROR": "RESOURCE_EXHAUSTED",
    "RATE_LIMIT_EXCEEDED": "RESOURCE_EXHAUSTED",
    "INSUFFICIENT_QUOTA": "RESOURCE_EXHAUSTED",
    "CONTENT_POLICY_VIOLATION": "CONTENT_BLOCKED",
    "SAFETY_VIOLATION": "CONTENT_BLOCKED",
    "SAFETY": "CONTENT_BLOCKED",
    "PROHIBITED_CONTENT": "CONTENT_BLOCKED",
    "BLOCKLIST": "CONTENT_BLOCKED",
    "IMAGE_SAFETY": "CONTENT_BLOCKED",
    "INTERNAL_SERVER_ERROR": "INTERNAL",
    "SERVER_ERROR": "INTERNAL",
}


def error_reason(payload):
    """Recognize structured codes and narrow message patterns without echoing text."""
    error = payload.get("error") if isinstance(payload, dict) else None
    if not isinstance(error, dict):
        return None, None
    code = None
    # A numeric code or unknown status must not hide a recognized type/reason.
    values = [error.get(key) for key in ("status", "type", "code", "reason")]
    details = error.get("details")
    if isinstance(details, list):
        values.extend(item.get("reason") for item in details if isinstance(item, dict))
    for value in values:
        if isinstance(value, str):
            candidate = ERROR_ALIASES.get(value.upper(), value.upper())
            if candidate in ERROR_HINTS and (
                code is None or candidate not in ("INVALID_REQUEST", "INVALID_ARGUMENT")
            ):
                code = candidate
                if code not in ("INVALID_REQUEST", "INVALID_ARGUMENT"):
                    break
    # Some endpoints supply only a numeric code and a message. Match known phrases
    # to static categories; never copy even part of an upstream message or field.
    message = error.get("message")
    message = message[:8192].lower() if isinstance(message, str) else ""
    if code in (None, "INVALID_REQUEST", "INVALID_ARGUMENT"):
        if re.search(
            r"blocked by (?:the |our )?(?:safety|content filters)|blocked for (?:an? )?(?:unspecified )?policy reason|violates? (?:the |our )?(?:content|safety) policy|content policy violation|safety filters? (?:blocked|rejected)",
            message,
        ):
            code = "CONTENT_BLOCKED"
        elif re.search(
            r"billing (?:is |has been )?(?:disabled|not enabled)|billing must be enabled",
            message,
        ):
            code = "FAILED_PRECONDITION"
        elif re.search(
            r"(?:quota|rate limit) (?:has been )?exceeded|insufficient (?:credits|quota)",
            message,
        ):
            code = "RESOURCE_EXHAUSTED"
    if code in ("INVALID_ARGUMENT", "INVALID_REQUEST"):
        # Translate recognized field names into useful wording, not arbitrary
        # upstream descriptions that may contain the prompt or signed URLs.
        fields = []
        for detail in details if isinstance(details, list) else []:
            violations = (
                detail.get("fieldViolations", []) if isinstance(detail, dict) else []
            )
            if isinstance(violations, list):
                fields.extend(
                    item.get("field") for item in violations if isinstance(item, dict)
                )
        field_hints = {
            "response_format.duration": "The provider rejected the requested video length. Choose a supported length before retrying.",
            "response_format.aspect_ratio": "The provider rejected the video aspect ratio. Choose a supported format before retrying.",
            "response_format.resolution": "The provider rejected the output resolution. Choose a supported resolution before retrying.",
            "model": "The provider rejected the selected model. Check model availability and access before retrying.",
        }
        for field in fields:
            if isinstance(field, str) and field in field_hints:
                return code, field_hints[field]
    return code, ERROR_HINTS.get(code)


def provider_error(response):
    try:
        payload = response.json()
    except ValueError:
        payload = None
    code, hint = error_reason(payload)
    prefix = f"Video provider rejected the request (HTTP {response.status_code})"
    if code:
        return f"{prefix} [{code}]. {hint}"
    fallback = {
        401: "UNAUTHENTICATED",
        402: "PAYMENT_REQUIRED",
        403: "PERMISSION_DENIED",
    }.get(response.status_code)
    if fallback:
        return f"{prefix}. {ERROR_HINTS[fallback]}"
    if response.status_code == 429:
        return f"{prefix}. The provider is rate limiting requests. Wait and check your quota before retrying."
    if response.status_code >= 500:
        return f"{prefix}. The provider is having a server problem. Try again later."
    return f"{prefix}. The provider did not supply a recognized reason. Check the request settings and provider dashboard before retrying."


def poll(fetch, *, field="status", completed, pending, label):
    deadline = time.monotonic() + settings.VIDEO_GENERATION_TIMEOUT
    while time.monotonic() < deadline:
        payload = fetch()
        state = payload.get(field)
        if payload.get("error"):
            code, hint = error_reason(payload)
            raise VideoProviderError(
                f"{label} generation failed [{code}]. {hint}"
                if code
                else f"{label} generation failed. The provider did not supply a recognized reason. Check its dashboard before retrying."
            )
        if state in completed:
            return payload
        if state not in pending:
            raise VideoProviderError(f"{label} generation failed or was cancelled.")
        time.sleep(settings.VIDEO_POLL_INTERVAL)
    raise VideoProviderError(
        f"{label} generation timed out. The provider may still finish and charge "
        "for the request; check its dashboard before retrying."
    )


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,256}", value):
        raise VideoProviderError("Video provider returned an invalid job identifier.")
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
        raise VideoProviderError("Video provider returned an invalid API URL.")
    return value


def seconds_for(duration, minimum, maximum):
    value = duration or settings.SILENT_SCENE_SECONDS
    return max(minimum, min(maximum, math.ceil(value)))


def shot_prompt(prompt, style="", reference=None, *, audio_mode="AMBIENT"):
    text = f"One continuous shot, no cuts. {prompt}"
    text += (
        " No montage, internal cuts, fade to black, opening fade, or closing transition."
        " Keep the final action and reaction visible until the clip ends."
    )
    text += " " + audio_direction(audio_mode)
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
            raise VideoProviderError("Video provider returned an invalid download URL.")
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
                    raise VideoProviderError(
                        "Video download returned an invalid redirect."
                    )
                if (urlparse(target).hostname, urlparse(target).port) != (
                    parsed.hostname,
                    parsed.port,
                ):
                    download_headers = {}
                url = target
                continue
            if not 200 <= response.status_code < 300:
                raise VideoProviderError("Could not download the generated video.")
            with tempfile.SpooledTemporaryFile(max_size=1024 * 1024) as stream:
                count = 0
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    count += len(chunk)
                    if count > MAX_VIDEO_BYTES:
                        raise VideoProviderError(
                            "Generated video exceeds the 200 MB download limit."
                        )
                    stream.write(chunk)
                stream.seek(0)
                return save_stream(stream, directory)
    raise VideoProviderError("Video download returned too many redirects.")


def save_stream(stream, directory):
    Path(directory).mkdir(parents=True, exist_ok=True)
    path = str(Path(directory) / f"{uuid.uuid4()}.mp4")
    try:
        save_video(stream, path)
        return path
    except Exception:
        Path(path).unlink(missing_ok=True)
        raise
