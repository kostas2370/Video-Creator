from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("videomanagement", "0030_merge_custom_voices_and_scene_overlays")]

    operations = [
        migrations.AlterField(
            model_name="aiusage", name="service",
            field=models.CharField(max_length=10, choices=[
                ("text", "Text"), ("images", "Images"), ("tts", "Voice"),
                ("video", "Video"), ("stt", "Transcription"),
            ]),
        ),
        migrations.AddField(
            model_name="scene", name="caption_alignment",
            field=models.JSONField(default=dict, blank=True),
        ),
    ]
