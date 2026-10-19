from pathlib import Path

from django.core.files import File
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from apps.videomanagement.models import MediaAsset, SceneImage
from apps.videomanagement.services.media.music import set_music
from apps.videomanagement.services.scenes.editing import changed, editable_video
from apps.videomanagement.services.videos.manual import add_manual_scene
from apps.videomanagement.utils.file_utils import stored_file_exists


def delete_media_asset(asset):
    with transaction.atomic():
        file = asset.file
        asset.delete()
        transaction.on_commit(lambda: file.storage.delete(file.name), robust=True)


def use_media_asset(asset, video, *, purpose, scene_id=None, **options):
    if not stored_file_exists(asset.file):
        raise ValidationError("This library file is missing. Upload it again.")
    if (purpose == "music") != (asset.kind == MediaAsset.Kind.AUDIO):
        raise ValidationError(
            "Use audio as background music, and images or clips as scene visuals."
        )
    if purpose == "visual" and scene_id is None:
        raise ValidationError({"scene_id": "Choose a scene to replace its visual."})
    with asset.file.open("rb") as source:
        upload = File(source, name=Path(asset.file.name).name)
        if purpose == "music":
            set_music(video, upload)
            return None
        if purpose == "new_scene":
            return add_manual_scene(video, image=upload, **options)
        return replace_scene_visual(
            video, scene_id, upload, options.get("with_audio", False)
        )


def replace_scene_visual(video, scene_id, upload, with_audio):
    saved = None
    try:
        with editable_video(video.pk) as locked:
            scene = get_object_or_404(locked.scenes.select_for_update(), pk=scene_id)
            image = scene.scene_images.first() or SceneImage(scene=scene)
            old_file = image.file if image.pk else None
            image.file = upload
            image.with_audio = with_audio
            image.prompt = ""
            image.save()
            saved = image.file
            changed(locked)
            if old_file:
                transaction.on_commit(
                    lambda: old_file.storage.delete(old_file.name), robust=True
                )
        return scene
    except Exception:
        if saved:
            saved.storage.delete(saved.name)
        raise
