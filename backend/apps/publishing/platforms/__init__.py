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


def get_publisher(account, token=None):
    """Select a publisher; a token is only needed for remote operations."""
    return PUBLISHERS[account.platform](account, token)
