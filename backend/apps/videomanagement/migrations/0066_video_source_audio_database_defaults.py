from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("videomanagement", "0065_video_source_audio"),
    ]

    operations = [
        migrations.AlterField(
            model_name="video",
            name="source_audio",
            field=models.FileField(
                blank=True, db_default="", upload_to="media/narration/%Y/%m/%d"
            ),
        ),
        migrations.AlterField(
            model_name="video",
            name="source_audio_words",
            field=models.JSONField(
                blank=True, db_default=[], default=list, editable=False
            ),
        ),
    ]
