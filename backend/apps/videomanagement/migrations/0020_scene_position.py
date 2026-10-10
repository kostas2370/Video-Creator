from django.db import migrations, models


def backfill_positions(apps, schema_editor):
    Scene = apps.get_model("videomanagement", "Scene")
    database = schema_editor.connection.alias
    scenes = Scene.objects.using(database)
    video_ids = scenes.order_by().values_list("video_id", flat=True).distinct()
    for video_id in video_ids.iterator():
        batch = []
        for position, scene in enumerate(
            scenes.filter(video_id=video_id).order_by("created_at").iterator(), start=1
        ):
            scene.position = position
            batch.append(scene)
            if len(batch) == 500:
                scenes.bulk_update(batch, ["position"])
                batch = []
        if batch:
            scenes.bulk_update(batch, ["position"])


class Migration(migrations.Migration):
    dependencies = [("videomanagement", "0019_alter_scene_options_alter_sceneimage_options_and_more")]
    operations = [
        migrations.AddField(
            model_name="scene", name="position",
            field=models.PositiveIntegerField(null=True, editable=False),
        ),
        migrations.RunPython(backfill_positions, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="scene", name="position",
            field=models.PositiveIntegerField(default=None, editable=False),
        ),
        migrations.AlterModelOptions(name="scene", options={"ordering": ["position"]}),
        migrations.AddConstraint(
            model_name="scene",
            constraint=models.UniqueConstraint(fields=("video", "position"), name="unique_scene_position"),
        ),
    ]
