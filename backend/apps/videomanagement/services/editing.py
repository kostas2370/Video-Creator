from contextlib import contextmanager

from django.db import transaction
from django.shortcuts import get_object_or_404

from ..events import publish_update
from ..models import Scene, Video, VideoStatus
from ..utils.exceptions import VideoEditConflict


@contextmanager
def editable_video(video_id):
    """Serialize playback edits with scene creation and rendering claims."""
    with transaction.atomic():
        video = Video.objects.select_for_update().get(pk=video_id)
        if video.status not in (VideoStatus.READY, VideoStatus.COMPLETED, VideoStatus.FAILED):
            raise VideoEditConflict()
        yield video


def reorder_scenes(video, scene_ids):
    with editable_video(video.pk) as locked_video:
        scenes = list(locked_video.scenes.select_for_update())
        if len(scene_ids) != len(scenes) or set(scene_ids) != {scene.pk for scene in scenes}:
            raise VideoEditConflict("The scene list changed. Refresh and try again.")
        # Temporary positions above the current range allow swaps without
        # violating the unique video/position constraint.
        offset = max((scene.position for scene in scenes), default=0)
        for position, scene_id in enumerate(scene_ids, 1):
            locked_video.scenes.filter(pk=scene_id).update(position=offset + position)
        for position, scene_id in enumerate(scene_ids, 1):
            locked_video.scenes.filter(pk=scene_id).update(position=position)
        locked_video.save(update_fields=["updated_at"])
        publish_update(f"video.{locked_video.pk}", video_id=locked_video.pk)
    return locked_video


def update_scene_transition(scene, **changes):
    with editable_video(scene.video_id) as video:
        scene = get_object_or_404(Scene.objects.select_for_update(), pk=scene.pk)
        scene.transition_after = changes["transition_after"]
        if "transition_duration" in changes:
            scene.transition_duration = changes["transition_duration"]
        scene.save(update_fields=["transition_after", "transition_duration"])
        video.save(update_fields=["updated_at"])
        publish_update(f"video.{video.pk}", video_id=video.pk)
    return scene
