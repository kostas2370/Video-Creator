"""Keep independent library copies of project and character images."""
from pathlib import Path

from django.core.files import File

from apps.videomanagement.models import MediaAsset
from apps.videomanagement.utils.file_utils import stored_file_exists


def archive_reference(instance):
    model = instance._meta.model_name
    if model == "characterreference":
        fields = {"image": "character reference"}
        title = instance.description.get("name", "Character")
        owner = instance.created_by
        video = None
    elif model == "scene":
        fields = {"overlay_logo": "overlay logo"}
        video = instance.video
        owner = video.created_by
        title = f"{video.title} · Scene {instance.position}"
    else:
        fields = {"reference_image": "style reference"}
        if model == "video":
            fields.update(cover="cover", thumbnail="thumbnail")
        title = instance.title
        owner = instance.created_by
        video = instance if model == "video" else None
    if owner is None:
        return
    last_asset = None
    for field, tag in fields.items():
        image = getattr(instance, field, None)
        if not stored_file_exists(image):
            continue
        with image.open("rb") as source:
            asset = MediaAsset.from_visual(
                user=owner, upload=File(source, name=Path(image.name).name),
                title=f"{title} · {tag.capitalize()}", tags=[tag],
                kind=MediaAsset.Kind.IMAGE, source_video=video,
            )
        if tag not in asset.tags:
            asset.tags = [*asset.tags, tag]
            asset.save(update_fields=["tags"])
        last_asset = asset
    return last_asset
