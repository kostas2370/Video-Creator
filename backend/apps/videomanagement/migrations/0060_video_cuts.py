from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("videomanagement", "0059_scene_cuts")]
    operations = [
        migrations.AddField(
            model_name="video",
            name="cuts",
            field=models.JSONField(blank=True, default=dict, db_default={}),
        )
    ]
