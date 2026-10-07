"""Publish small invalidations after committed writes; Redis is optional to jobs."""
import asyncio
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

logger = logging.getLogger(__name__)


def publish_update(group, *, kind="video", video_id=None, scene_id=None, using=None):
    def publish():
        try:
            layer = get_channel_layer("video_events")
            async_to_sync(asyncio.wait_for)(
                layer.group_send(
                    group,
                    {"type": "video.update", "video_id": video_id,
                     "kind": kind, "scene_id": scene_id},
                ),
                timeout=1,
            )
        except Exception:
            # Notification delivery must never turn a successful edit/job into failure.
            logger.warning("Could not publish update for %s", group, exc_info=True)

    transaction.on_commit(publish, using=using)
