from django.db import transaction
from django_eventstream import send_event


def publish_update(group, *, kind="video", video_id=None, scene_id=None, using=None):
    transaction.on_commit(
        lambda: send_event(
            group,
            "update",
            {"video_id": video_id, "kind": kind, "scene_id": scene_id},
        ),
        using=using,
        robust=True,
    )
