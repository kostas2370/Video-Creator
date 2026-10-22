"""Select account connection operations for a social platform."""

from ..config import configuration
from ..models import Platform
from . import meta, tiktok, youtube

CONNECTIONS = {Platform.YOUTUBE: youtube, Platform.TIKTOK: tiktok, Platform.INSTAGRAM: meta}


def get_connection(platform):
    configuration(platform)
    return CONNECTIONS[platform]
