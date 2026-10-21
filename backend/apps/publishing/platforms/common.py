"""Shared publishing validation, job persistence and binary transfers."""

import requests
from rest_framework.exceptions import ValidationError

from ..http import ProviderError


def validate_caption(caption):
    if len(caption.encode("utf-16-le")) // 2 > 2200:
        raise ValidationError({"caption": "Use at most 2200 characters, counting emoji as two characters."})


def update(job, **values):
    for key, value in values.items():
        setattr(job, key, value)
    job.save(update_fields=[*values, "updated_at"])


def put_binary(url, *, data, headers):
    try:
        response = requests.put(url, data=data, headers=headers, timeout=(10, 300), allow_redirects=False)
    except requests.RequestException as exc:
        raise ProviderError("The transfer was interrupted. Check the platform before starting another upload.") from exc
    if response.status_code not in (200, 201, 204, 206):
        raise ProviderError("The platform did not confirm the transfer. Check its status before trying again.")
    return response

