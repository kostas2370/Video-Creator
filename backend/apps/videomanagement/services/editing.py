from contextlib import contextmanager
from pathlib import Path

from django.db import transaction
from django.shortcuts import get_object_or_404

from ..events import publish_update
from ..models import Scene, Video, VideoStatus
from ..utils.exceptions import VideoEditConflict


@contextmanager
def editable_video(video_id):
    """Hold the video lock through the edit; commit or roll back on exit."""
    with transaction.atomic():
        video = get_object_or_404(Video.objects.select_for_update(), pk=video_id)
        if video.status not in (VideoStatus.READY, VideoStatus.COMPLETED, VideoStatus.FAILED):
            raise VideoEditConflict()
        yield video


def reorder_scenes(video, scene_ids):
    with editable_video(video.pk) as locked_video:
        scenes = list(locked_video.scenes.select_for_update())
        if len(scene_ids) != len(scenes) or set(scene_ids) != {scene.pk for scene in scenes}:
            raise VideoEditConflict("The scene list changed. Refresh and try again.")
        if scene_ids == [scene.pk for scene in scenes]:
            return locked_video
        by_id = {scene.pk: scene for scene in scenes}
        ordered = [by_id[scene_id] for scene_id in scene_ids]
        # Temporary positions above the current range allow swaps without
        # violating the unique video/position constraint.
        offset = max(scene.position for scene in scenes)
        for position, scene in enumerate(ordered, 1):
            scene.position = offset + position
        Scene.objects.bulk_update(ordered, ["position"])
        for position, scene in enumerate(ordered, 1):
            scene.position = position
        Scene.objects.bulk_update(ordered, ["position"])
        locked_video.save(update_fields=["updated_at"])
        publish_update(f"video.{locked_video.pk}", video_id=locked_video.pk)
    return locked_video


def update_scene_transition(scene, **changes):
    return _update_playback(scene, ("transition_after", "transition_duration"), changes)


def update_scene_timing(scene, **changes):
    return _update_playback(scene, ("pause_after",), changes)


def _update_playback(scene, allowed_fields, changes):
    with editable_video(scene.video_id) as video:
        scene = get_object_or_404(Scene.objects.select_for_update(), pk=scene.pk)
        fields = [field for field in allowed_fields
                  if field in changes and getattr(scene, field) != changes[field]]
        if not fields:
            return scene
        for field in fields:
            setattr(scene, field, changes[field])
        scene.save(update_fields=fields)
        if "pause_after" in fields and video.avatar_id:
            transaction.on_commit(lambda: Path(video.dir_name, "output_avatar.mp4").unlink(missing_ok=True), robust=True)
        video.save(update_fields=["updated_at"])
        publish_update(f"video.{video.pk}", video_id=video.pk)
    return scene
