"""Retention and permanent cleanup for recoverable scene removals."""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.videomanagement.models import Scene, Video, VideoStatus

SCENE_RETENTION = timedelta(days=7)


def recoverable_scenes(video):
    return Scene.all_objects.filter(
        video=video, archived_at__gt=timezone.now() - SCENE_RETENTION
    ).order_by("-archived_at", "id")


def purge_expired_scenes(*, now=None, batch_size=500):
    cutoff = (now or timezone.now()) - SCENE_RETENTION
    candidates = list(
        Scene.all_objects.filter(
            archived_at__lte=cutoff,
            video__status__in=(
                VideoStatus.READY,
                VideoStatus.COMPLETED,
                VideoStatus.FAILED,
            ),
        )
        .order_by("archived_at")
        .values_list("pk", "video_id")[:batch_size]
    )
    deleted = 0
    for scene_id, video_id in candidates:
        # Use the same lock order as editing/restoring and recheck after locking.
        with transaction.atomic():
            video = Video.objects.select_for_update().filter(pk=video_id).first()
            if not video or video.status not in (
                VideoStatus.READY,
                VideoStatus.COMPLETED,
                VideoStatus.FAILED,
            ):
                continue
            scene = (
                Scene.all_objects.select_for_update()
                .filter(pk=scene_id, archived_at__lte=cutoff)
                .first()
            )
            if scene:
                scene.delete()
                deleted += 1
    return {"deleted": deleted, "examined": len(candidates)}
