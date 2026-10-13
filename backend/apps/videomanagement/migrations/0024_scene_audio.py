from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("videomanagement", "0023_scene_pause_after")]
    operations = [
        migrations.AddField(model_name="scene", name="voiceover", field=models.FileField(blank=True, max_length=2000, upload_to="media/voiceovers")),
        migrations.AddField(model_name="scene", name="audio_settings", field=models.JSONField(blank=True, default=dict)),
    ]
