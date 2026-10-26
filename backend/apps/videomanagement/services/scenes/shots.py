from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from apps.videomanagement.exceptions import VideoEditConflict
from apps.videomanagement.models import Scene
from apps.videomanagement.utils.file_utils import check_if_video
from apps.videomanagement.utils.timing import file_timing, scene_timing
from .editing import changed, editable_video


def next_shot_position(scene):
    images = list(scene.scene_images.all())
    if len(images) >= 20:
        raise ValidationError("A scene can contain up to 20 shots.")
    if len(images) == 1:
        settings = dict(scene.audio_settings or {})
        settings["visual_track_duration"] = scene_timing(scene, images[0])[
            "base_duration"
        ]
        scene.audio_settings = settings
        scene.save(update_fields=["audio_settings"])
    return max((image.position for image in images), default=-1) + 1


def update_shots(scene, shots, expected_ids):
    with editable_video(scene.video_id) as video:
        scene = get_object_or_404(Scene.objects.select_for_update(), pk=scene.pk)
        images = list(scene.scene_images.select_for_update())
        if [row.pk for row in images] != expected_ids:
            raise VideoEditConflict("The shots changed. Refresh and try again.")
        by_id = {row.pk: row for row in images}
        if any(shot["id"] not in by_id for shot in shots):
            raise ValidationError("Choose shots belonging to this scene.")
        for position, data in enumerate(shots):
            image = by_id[data["id"]]
            if data["trim_start"]:
                duration = (
                    file_timing(image.file).get("duration")
                    if image.file and check_if_video(image.file.name)
                    else None
                )
                if duration is None or data["trim_start"] >= duration:
                    raise ValidationError(
                        "The trim point must be inside the video clip."
                    )
            image.position = position
            for key, value in data.items():
                if key != "id":
                    setattr(image, key, value)
            image.save()
        scene.scene_images.exclude(pk__in=[shot["id"] for shot in shots]).delete()
        changed(video, invalidate_avatar=False)
    return scene
