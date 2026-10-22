"""Shared platform requests; errors omit credentials and response bodies."""

from urllib.parse import urlparse

import requests

from .models import Platform


class ProviderError(Exception):
    SAFE_CODES = {
        "access_denied", "invalid_client", "invalid_grant", "invalid_request",
        "invalid_scope", "unauthorized_client", "access_token_invalid",
        "scope_not_authorized", "invalid_token", "rate_limit_exceeded",
        "server_error", "temporarily_unavailable",
        "unaudited_client_can_only_post_to_private_accounts", "privacy_level_option_mismatch",
        "spam_risk_too_many_posts", "spam_risk_user_banned_from_posting", "reached_active_user_cap",
    }

    def __init__(self, message, *, code=None, status=None):
        super().__init__(message)
        self.provider_code = code if isinstance(code, str) and code in self.SAFE_CODES else None
        self.http_status = status
        self.stage = None


class UploadRejected(ProviderError):
    """A confirmed rejection before media transfer, with a safe user message."""


def request_json(method, url, token=None, **kwargs):
    """Send a platform request and return a JSON object, with sanitized errors."""
    headers = dict(kwargs.pop("headers", {}))
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.request(
            method, url, headers=headers,
            timeout=(10, 90), allow_redirects=False, **kwargs,
        )
    except requests.RequestException as exc:
        raise ProviderError("The platform request did not complete. Check its status before trying another upload.") from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise ProviderError("The platform returned an unexpected response.", status=response.status_code) from exc

    error = data.get("error") if isinstance(data, dict) else None
    code = error.get("code") if isinstance(error, dict) else error
    if not 200 <= response.status_code < 300:
        raise ProviderError("The platform rejected the request. Check the account permissions and posting settings.", code=code, status=response.status_code)
    if not isinstance(data, dict):
        raise ProviderError("The platform returned an unexpected response.")

    if error:
        # TikTok includes an error object with code "ok" on successful requests.
        is_success_status = isinstance(error, dict) and error.get("code") in (None, "ok", 0)
        if not is_success_status:
            raise ProviderError("The platform could not complete the request. Check account permissions and posting limits.", code=code, status=response.status_code)
    return data


def checked_upload_url(url, platform):
    parsed = urlparse(url)
    host = parsed.hostname or ""
    allowed = host == "www.googleapis.com" if platform == Platform.YOUTUBE else host.endswith(".tiktokapis.com")
    try:
        valid_port = parsed.port in (None, 443)
    except ValueError:
        valid_port = False
    if parsed.scheme != "https" or not allowed or not valid_port or parsed.username or parsed.password:
        raise ProviderError("The platform returned an unsupported upload address.")
    return url
