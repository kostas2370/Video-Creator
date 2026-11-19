from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("videomanagement", "0066_video_source_audio_database_defaults")]

    operations = [
        migrations.AddField(
            model_name="video",
            name="generation_error",
            field=models.JSONField(
                blank=True, default=dict, db_default={}, editable=False
            ),
        ),
    ]
