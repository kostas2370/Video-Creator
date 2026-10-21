"""Make existing scene files assets without moving or copying their bytes."""

from pathlib import Path

from django.db import migrations

VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".webm", ".m4v"}


def backfill_visual_assets(apps, schema_editor):
    Asset = apps.get_model("videomanagement", "MediaAsset")
    Visual = apps.get_model("videomanagement", "SceneImage")
    alias = schema_editor.connection.alias
    assets = Asset.objects.using(alias)
    visuals = Visual.objects.using(alias).select_related("scene__video")
    for visual in visuals.iterator(chunk_size=200):
        if not visual.file:
            continue
        video = visual.scene.video
        kind = (
            "VIDEO"
            if Path(visual.file.name).suffix.lower() in VIDEO_EXTENSIONS
            else "IMAGE"
        )
        asset = assets.filter(
            created_by_id=video.created_by_id, file=visual.file.name
        ).first() or assets.create(
            created_by_id=video.created_by_id,
            file=visual.file.name,
            title=f"{video.title} · Scene {visual.scene.position}"[:100],
            tags=["scene video" if kind == "VIDEO" else "scene image"],
            kind=kind,
            source_video_id=video.pk,
            created_at=visual.created_at,
        )
        Visual.objects.using(alias).filter(pk=visual.pk).update(asset_id=asset.pk)


class Migration(migrations.Migration):
    dependencies = [("videomanagement", "0038_persistent_visual_assets")]
    operations = [
        migrations.RunPython(backfill_visual_assets, migrations.RunPython.noop)
    ]
