from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("videomanagement", "0045_scene_shot_plan")]

    operations = [
        migrations.AddField(
            model_name="scene",
            name="script_index",
            field=models.PositiveIntegerField(null=True, blank=True, editable=False),
        ),
        migrations.AddField(
            model_name="video",
            name="render_error",
            field=models.JSONField(default=dict, blank=True),
        ),
    ]
