from contextlib import contextmanager
from pathlib import Path

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.videomanagement.events import publish_update
from apps.videomanagement.exceptions import VideoEditConflict
from apps.videomanagement.models import (
    MotionStyle,
    Scene,
    SceneImage,
    Video,
    VideoStatus,
)
from apps.videomanagement.utils.file_utils import check_if_image


def changed(video, *, invalidate_avatar=True):
    """Refresh the editor and discard avatar audio only when the edit affects it."""
    video.save(update_fields=["updated_at"])
    if invalidate_avatar and video.avatar_id:
        transaction.on_commit(
            lambda: Path(video.dir_name, "output_avatar.mp4").unlink(missing_ok=True),
            robust=True,
        )
    publish_update(f"video.{video.pk}", video_id=video.pk)


@contextmanager
def editable_video(video_id):
    """Hold the video lock through the edit; commit or roll back on exit."""
    with transaction.atomic():
        video = get_object_or_404(Video.objects.select_for_update(), pk=video_id)
        if video.status not in (
            VideoStatus.READY,
            VideoStatus.COMPLETED,
            VideoStatus.FAILED,
        ):
            raise VideoEditConflict()
        yield video


def reorder_scenes(video, scene_ids, expected_scene_ids=None):
    with editable_video(video.pk) as locked_video:
        scenes = list(locked_video.scenes.select_for_update())
        if expected_scene_ids is not None and expected_scene_ids != [row.pk for row in scenes]:
            raise VideoEditConflict("The scene order changed in another session. Refresh before undoing.")
        if len(scene_ids) != len(scenes) or set(scene_ids) != {
            scene.pk for scene in scenes
        }:
            raise VideoEditConflict("The scene list changed. Refresh and try again.")
        if scene_ids == [scene.pk for scene in scenes]:
            return locked_video
        by_id = {scene.pk: scene for scene in scenes}
        archived = list(Scene.all_objects.filter(video=locked_video, archived_at__isnull=False).select_for_update())
        ordered = [by_id[scene_id] for scene_id in scene_ids] + archived
        # Temporary positions above the current range allow swaps without
        # violating the unique video/position constraint.
        offset = max(scene.position for scene in ordered)
        for position, scene in enumerate(ordered, 1):
            scene.position = offset + position
        Scene.all_objects.bulk_update(ordered, ["position"])
        for position, scene in enumerate(ordered, 1):
            scene.position = position
        Scene.all_objects.bulk_update(ordered, ["position"])
        changed(locked_video, invalidate_avatar=False)
    return locked_video


def apply_auto_motion(video, intensity):
    with editable_video(video.pk) as locked_video:
        scenes = (
            locked_video.scenes.exclude(
                motion_style=MotionStyle.AUTO, motion_intensity=intensity
            )
            .select_for_update()
            .with_media()
        )
        scene_ids = []
        for scene in scenes:
            image = next(iter(scene.scene_images.all()), None)
            if image and image.file and check_if_image(image.file.name):
                scene_ids.append(scene.pk)
        if scene_ids:
            locked_video.scenes.filter(pk__in=scene_ids).update(
                motion_style=MotionStyle.AUTO,
                motion_intensity=intensity,
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
        updates = {
            field: changes[field]
            for field in allowed_fields
            if field != "duration"
            and field in changes
            and getattr(scene, field) != changes[field]
        }
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
        changed(
            video,
            invalidate_avatar=bool({"pause_after", "audio_settings"} & updates.keys()),
        )
    return scene


def update_manual_text(scene, text):
    with editable_video(scene.video_id) as video:
        scene = get_object_or_404(Scene.objects.select_for_update(), pk=scene.pk)
        scene.text = text
        scene.save(update_fields=["text"])
        changed(video)
    return scene


def delete_scene(scene):
    with editable_video(scene.video_id) as video:
        return archive_scene(scene, list(video.scenes.values_list("pk", flat=True)))


def archive_scene(scene, scene_ids):
    """Remove a scene from playback while retaining its media for Undo."""
    with editable_video(scene.video_id) as video:
        current = list(video.scenes.select_for_update().values_list("pk", flat=True))
        if current != scene_ids:
            raise VideoEditConflict("The scene list changed. Refresh before removing a scene.")
        scene = get_object_or_404(Scene.objects.select_for_update(), pk=scene.pk)
        scene.archived_at = timezone.now()
        scene.archived_position = current.index(scene.pk) + 1
        scene.save(update_fields=["archived_at", "archived_position"])
        changed(video)
    return video


def restore_scene(scene, expected_scene_ids, scene_ids=None):
    with editable_video(scene.video_id) as video:
        scene = get_object_or_404(Scene.all_objects.select_for_update(), pk=scene.pk)
        current = list(video.scenes.select_for_update())
        from .recovery import SCENE_RETENTION

        if scene.archived_at is not None and scene.archived_at <= timezone.now() - SCENE_RETENTION:
            raise VideoEditConflict("This scene’s 7-day recovery window has expired.")
        if scene.archived_at is None or expected_scene_ids != [row.pk for row in current]:
            raise VideoEditConflict("The scene list changed. Refresh before undoing.")
        if scene_ids is None:
            scene_ids = [row.pk for row in current]
            scene_ids.insert(min(max((scene.archived_position or len(current) + 1) - 1, 0), len(current)), scene.pk)
        if len(scene_ids) != len(current) + 1 or set(scene_ids) != {scene.pk, *(row.pk for row in current)}:
            raise VideoEditConflict("The scene list changed. Refresh before undoing.")
        # Restore outside the occupied range, then reuse the transactional reorder.
        scene.position = max(Scene.all_objects.filter(video=video).values_list("position", flat=True), default=0) + 1
        scene.archived_at = None
        scene.archived_position = None
        scene.save(update_fields=["position", "archived_at", "archived_position"])
        reorder_scenes(video, scene_ids)
        changed(video)
    return video


def clear_scene_image(image):
    with editable_video(image.scene.video_id) as video:
        image.file = None
        image.save()
        changed(video)


def update_scene_image(scene, scene_image=None, *, image=None, with_audio=False):
    try:
        with editable_video(scene.video_id) as video:
            if scene_image is not None:
                scene_image = get_object_or_404(
                    SceneImage.objects.select_for_update(),
                    pk=scene_image.pk,
                    scene_id=scene.pk,
                )
            else:
                scene_image = SceneImage(scene=scene)
            if image:
                scene_image.file = image
            scene_image.with_audio = with_audio
            scene_image.save()
            changed(video)
        return scene_image
    except Exception:
        if scene_image:
            scene_image.discard_upload()
        raise
