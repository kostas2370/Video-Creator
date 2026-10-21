from django.db import migrations


def restore_scene_files(apps, schema_editor):
    Visual = apps.get_model("videomanagement", "SceneImage")
    visuals = Visual.objects.using(schema_editor.connection.alias)
    for visual in (
        visuals.select_related("asset")
        .filter(asset__isnull=False)
        .iterator(chunk_size=200)
    ):
        visuals.filter(pk=visual.pk).update(file=visual.asset.file.name)


class Migration(migrations.Migration):
    dependencies = [("videomanagement", "0039_backfill_visual_assets")]
    operations = [
        migrations.RunPython(migrations.RunPython.noop, restore_scene_files),
        migrations.RemoveField(model_name="sceneimage", name="file"),
    ]
