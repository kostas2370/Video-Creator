from contextlib import contextmanager
from pathlib import Path

from django.db import transaction
from django.shortcuts import get_object_or_404

from ..events import publish_update
from ..models import Scene, Video, VideoStatus, MotionStyle
from ..utils.file_utils import check_if_image
from ..utils.exceptions import VideoEditConflict


def changed(video, *, invalidate_avatar=True):
    """Refresh the editor and discard avatar audio only when the edit affects it."""
    video.save(update_fields=["updated_at"])
    if invalidate_avatar and video.avatar_id:
        transaction.on_commit(lambda: Path(video.dir_name, "output_avatar.mp4").unlink(missing_ok=True), robust=True)
    publish_update(f"video.{video.pk}", video_id=video.pk)


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
        changed(locked_video, invalidate_avatar=False)
    return locked_video


def apply_auto_motion(video, intensity):
    with editable_video(video.pk) as locked_video:
        scenes = (
            locked_video.scenes.exclude(motion_style=MotionStyle.AUTO, motion_intensity=intensity)
            .select_for_update()
            .prefetch_related("scene_images")
        )
        scene_ids = []
        for scene in scenes:
            image = next(iter(scene.scene_images.all()), None)
            if image and image.file and check_if_image(image.file.name):
                scene_ids.append(scene.pk)
        if scene_ids:
            locked_video.scenes.filter(pk__in=scene_ids).update(
                motion_style=MotionStyle.AUTO, motion_intensity=intensity,
            )
            changed(locked_video, invalidate_avatar=False)
    return locked_video


def update_scene_transition(scene, **changes):
    return _update_playback(scene, ("transition_after", "transition_duration"), changes)


def update_scene_motion(scene, **changes):
    return _update_playback(scene, ("motion_style", "motion_intensity"), changes)


def update_scene_timing(scene, **changes):
    return _update_playback(scene, ("pause_after", "duration"), changes)


def _update_playback(scene, allowed_fields, changes):
    with editable_video(scene.video_id) as video:
        scene = get_object_or_404(Scene.objects.select_for_update(), pk=scene.pk)
        updates = {field: changes[field] for field in allowed_fields
                   if field != "duration" and field in changes
                   and getattr(scene, field) != changes[field]}
        if "duration" in allowed_fields and "duration" in changes:
            settings = dict(scene.audio_settings or {})
            if changes["duration"] is None:
                settings.pop("duration", None)
            else:
                settings["duration"] = changes["duration"]
            if settings != scene.audio_settings:
                updates["audio_settings"] = settings
        if not updates:
            return scene
        for field, value in updates.items():
            setattr(scene, field, value)
        scene.save(update_fields=list(updates))
        changed(video, invalidate_avatar=bool({"pause_after", "audio_settings"} & updates.keys()))
    return scene
