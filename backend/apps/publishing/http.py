"""Shared platform requests; errors omit credentials and response bodies."""

from urllib.parse import urlparse

import requests

from .models import Platform


class ProviderError(Exception):
    pass


def api(method, url, token=None, **kwargs):
    headers = dict(kwargs.pop("headers", {}))
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.request(method, url, headers=headers, timeout=(10, 90), allow_redirects=False, **kwargs)
        if not 200 <= response.status_code < 300:
            raise ProviderError("The platform rejected the request. Check the account permissions and posting settings.")
        data = response.json()
        if not isinstance(data, dict):
            raise ProviderError("The platform returned an unexpected response.")
        error = data.get("error")
        if error and (not isinstance(error, dict) or error.get("code") not in (None, "ok", 0)):
            raise ProviderError("The platform could not complete the request. Check account permissions and posting limits.")
        return data
    except (requests.RequestException, ValueError) as exc:
        raise ProviderError("The platform request did not complete. Check its status before trying another upload.") from exc


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
