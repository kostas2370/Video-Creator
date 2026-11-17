"""Public video errors contain only application-authored, safe explanations."""

from rest_framework.exceptions import APIException


class VideoProviderError(APIException):
    """An error safe to persist and return through a scene job.

    Never construct this with raw provider messages, prompts, URLs or credentials.
    Keep the constructor compatible with Celery exception serialization.
    """


def public_video_error(error):
    return str(error) if isinstance(error, VideoProviderError) else None
