from django.db import migrations, models


def order_visuals(apps, schema_editor):
    Image = apps.get_model("videomanagement", "SceneImage")
    current, position = None, 0
    for image in (
        Image.objects.using(schema_editor.connection.alias)
        .order_by("scene_id", "created_at", "id")
        .iterator()
    ):
        if image.scene_id != current:
            current, position = image.scene_id, 0
        image.position = position
        image.save(update_fields=["position"], using=schema_editor.connection.alias)
        position += 1


class Migration(migrations.Migration):
    dependencies = [("videomanagement", "0045_scene_shot_plan")]
    operations = [
        migrations.AddField(
            model_name="sceneimage",
            name="position",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="sceneimage",
            name="timing_weight",
            field=models.FloatField(default=1),
        ),
        migrations.AddField(
            model_name="sceneimage",
            name="trim_start",
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name="sceneimage",
            name="motion_style",
            field=models.CharField(
                blank=True,
                choices=[
                    ("NONE", "None"),
                    ("AUTO", "Auto"),
                    ("ZOOM_IN", "Zoom In"),
                    ("ZOOM_OUT", "Zoom Out"),
                    ("PAN_LEFT", "Pan Left"),
                    ("PAN_RIGHT", "Pan Right"),
                    ("PAN_UP", "Pan Up"),
                    ("PAN_DOWN", "Pan Down"),
                ],
                max_length=10,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="sceneimage",
            name="motion_intensity",
            field=models.CharField(
                blank=True,
                choices=[
                    ("SUBTLE", "Subtle"),
                    ("MEDIUM", "Medium"),
                    ("STRONG", "Strong"),
                ],
                max_length=6,
                null=True,
            ),
        ),
        migrations.RunPython(order_visuals, migrations.RunPython.noop),
        migrations.AlterModelOptions(
            name="sceneimage", options={"ordering": ["position", "created_at", "id"]}
        ),
    ]
