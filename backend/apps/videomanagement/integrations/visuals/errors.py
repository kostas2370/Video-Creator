"""Public video errors contain only application-authored, safe explanations."""

import re

from rest_framework.exceptions import APIException


class VideoProviderError(APIException):
    """An error safe to persist and return through a scene job.

    Never construct this with raw provider messages, prompts, URLs or credentials.
    Keep the constructor compatible with Celery exception serialization.
    """


def public_video_error(error):
    return str(error) if isinstance(error, VideoProviderError) else None


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

FIELD_HINTS = {
    "response_format.duration": "The provider rejected the requested video length. Choose a supported length before retrying.",
    "response_format.aspect_ratio": "The provider rejected the video aspect ratio. Choose a supported format before retrying.",
    "response_format.resolution": "The provider rejected the output resolution. Choose a supported resolution before retrying.",
    "model": "The provider rejected the selected model. Check model availability and access before retrying.",
}
GENERIC_CODES = {"INVALID_REQUEST", "INVALID_ARGUMENT"}
MESSAGE_PATTERNS = (
    (
        "CONTENT_BLOCKED",
        re.compile(
            r"blocked by (?:the |our )?(?:safety|content filters)|"
            r"blocked for (?:an? )?(?:unspecified )?policy reason|"
            r"violates? (?:the |our )?(?:content|safety) policy|"
            r"content policy violation|safety filters? (?:blocked|rejected)"
        ),
    ),
    (
        "FAILED_PRECONDITION",
        re.compile(
            r"billing (?:is |has been )?(?:disabled|not enabled)|billing must be enabled"
        ),
    ),
    (
        "RESOURCE_EXHAUSTED",
        re.compile(
            r"(?:quota|rate limit) (?:has been )?exceeded|insufficient (?:credits|quota)"
        ),
    ),
)


def _structured_code(error, details):
    """Prefer a specific allowlisted reason over a generic request error."""
    values = [error.get(key) for key in ("status", "type", "code", "reason")]
    values.extend(detail.get("reason") for detail in details)
    generic = None
    for value in values:
        if not isinstance(value, str):
            continue
        code = ERROR_ALIASES.get(value.upper(), value.upper())
        if code not in ERROR_HINTS:
            continue
        if code not in GENERIC_CODES:
            return code
        generic = generic or code
    return generic


def _message_code(message):
    """Map known phrases to static hints without copying provider text."""
    if isinstance(message, str):
        message = message[:8192].lower()
        for code, pattern in MESSAGE_PATTERNS:
            if pattern.search(message):
                return code
    return None


def _field_hint(details):
    for detail in details:
        violations = detail.get("fieldViolations", [])
        if not isinstance(violations, list):
            continue
        for violation in violations:
            field = violation.get("field") if isinstance(violation, dict) else None
            if isinstance(field, str) and field in FIELD_HINTS:
                return FIELD_HINTS[field]
    return None


def error_reason(payload):
    """Return only an allowlisted code and an application-authored hint."""
    error = payload.get("error") if isinstance(payload, dict) else None
    if not isinstance(error, dict):
        return None, None
    details = error.get("details")
    details = (
        [item for item in details if isinstance(item, dict)]
        if isinstance(details, list)
        else []
    )
    code = _structured_code(error, details)
    if code is None or code in GENERIC_CODES:
        code = _message_code(error.get("message")) or code
    hint = ERROR_HINTS.get(code)
    if code in GENERIC_CODES:
        hint = _field_hint(details) or hint
    return code, hint


def generation_error(label, payload, *, fallback=None):
    """Format the same safe reason for immediate and polled failures."""
    code, hint = error_reason(payload)
    if code:
        message = f"{label} generation failed [{code}]. {hint}"
    else:
        message = fallback or (
            f"{label} generation failed. The provider did not supply a recognized "
            "reason. Check its dashboard before retrying."
        )
    return VideoProviderError(message)


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
