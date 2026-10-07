import logging

from django.db import transaction
from django_eventstream import send_event

logger = logging.getLogger(__name__)


def publish_update(group, *, kind="video", video_id=None, scene_id=None, using=None):
    def publish():
        try:
            send_event(
                group,
                "update",
                {"video_id": video_id, "kind": kind, "scene_id": scene_id},
            )
        except Exception:
            logger.warning("Could not publish update for %s", group, exc_info=True)

    transaction.on_commit(publish, using=using)
