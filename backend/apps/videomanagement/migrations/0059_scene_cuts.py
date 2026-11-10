from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("videomanagement", "0058_rename_starting_frame_context")]
    operations = [
        migrations.AddField(
            model_name="scene",
            name="cuts",
            field=models.JSONField(default=dict, blank=True),
        )
    ]
