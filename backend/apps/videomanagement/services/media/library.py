from pathlib import Path

from django.core.files import File
from django.db import transaction
from django.db.models.deletion import RestrictedError
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from apps.videomanagement.models import MediaAsset, SceneImage
from apps.videomanagement.serializers.covers import CoverSerializer
from apps.videomanagement.services.media.covers import save_cover
from apps.videomanagement.services.media.music import set_music
from apps.videomanagement.services.scenes.editing import changed, editable_video
from apps.videomanagement.services.videos.manual import add_manual_scene
from apps.videomanagement.utils.file_utils import stored_file_exists


def delete_media_asset(asset):
    with transaction.atomic():
        try:
            asset.delete()
        except RestrictedError as exc:
            raise ValidationError(
                "This asset is used by a video. Remove it from its scenes first."
            ) from exc


def use_media_asset(asset, video, *, purpose, scene_id=None, **options):
    if not stored_file_exists(asset.file):
        raise ValidationError("This library file is missing. Upload it again.")
    if (purpose == "music") != (asset.kind == MediaAsset.Kind.AUDIO):
        raise ValidationError(
            "Use audio as background music, and images or clips as scene visuals."
        )
    if purpose == "cover" and asset.kind != MediaAsset.Kind.IMAGE:
        raise ValidationError("Choose an image for a video cover.")
    if purpose == "visual" and scene_id is None:
        raise ValidationError({"scene_id": "Choose a scene to replace its visual."})
    if purpose == "new_scene":
        return add_manual_scene(video, asset=asset, **options)
    if purpose == "visual":
        return replace_scene_visual(
            video, scene_id, asset, options.get("with_audio", False)
        )
    with asset.file.open("rb") as source:
        upload = File(source, name=Path(asset.file.name).name)
        if purpose == "cover":
            choices = CoverSerializer(
                data={"source": "upload", "image": upload, "title": ""}
            )
            choices.is_valid(raise_exception=True)
            save_cover(video, choices.validated_data)
            return None
        if purpose == "music":
            set_music(video, upload)
            return None


def replace_scene_visual(video, scene_id, asset, with_audio):
    with editable_video(video.pk) as locked:
        scene = get_object_or_404(locked.scenes.select_for_update(), pk=scene_id)
        image = scene.scene_images.first() or SceneImage(scene=scene)
        image.asset = asset
        image.with_audio = with_audio
        image.prompt = ""
        image.save()
        changed(locked)
    return scene
