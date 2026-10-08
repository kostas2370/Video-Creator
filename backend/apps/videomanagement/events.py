from django.db import transaction
from django_eventstream import send_event


def publish_update(group, *, kind="video", video_id=None, scene_id=None, using=None):
    transaction.on_commit(
        lambda: send_event(
            group,
            "update",
            {"video_id": str(video_id) if video_id is not None else None, "kind": kind, "scene_id": str(scene_id) if scene_id is not None else None},
        ),
        using=using,
        robust=True,
    )
