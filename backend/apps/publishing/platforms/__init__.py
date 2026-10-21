"""Select a publisher from the connected account's platform."""

from ..models import Platform
from .instagram import InstagramPublisher
from .tiktok import TikTokPublisher
from .youtube import YouTubePublisher

PUBLISHERS = {
    Platform.YOUTUBE: YouTubePublisher,
    Platform.TIKTOK: TikTokPublisher,
    Platform.INSTAGRAM: InstagramPublisher,
}


def get_publisher(account, token):
    return PUBLISHERS[account.platform](account, token)


def upload_video(job, token):
    """Upload the job's immutable video export to its connected account."""
    get_publisher(job.account, token).upload(job)


def check_status(job, token):
    get_publisher(job.account, token).check_status(job)
