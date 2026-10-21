"""Dispatch publishing through the connected account's platform."""

from ..models import Platform
from . import instagram, tiktok, youtube

PROVIDERS = {
    Platform.YOUTUBE: youtube,
    Platform.TIKTOK: tiktok,
    Platform.INSTAGRAM: instagram,
}


def upload_video(job, token):
    """Upload the job's immutable video export to its connected account."""
    return PROVIDERS[job.account.platform].upload(job, token)


def check_status(job, token):
    return PROVIDERS[job.account.platform].check_status(job, token)
