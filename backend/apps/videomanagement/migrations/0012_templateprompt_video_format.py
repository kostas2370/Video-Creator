from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("videomanagement", "0011_normalize_tts_provider_names"),
    ]

    operations = [
        migrations.AddField(
            model_name="templateprompt",
            name="video_format",
            field=models.CharField(
                choices=[
                    ("LANDSCAPE", "Landscape (16:9)"),
                    ("PORTRAIT", "Portrait (9:16)"),
                    ("SQUARE", "Square (1:1)"),
                ],
                default="LANDSCAPE",
                max_length=12,
            ),
        ),
    ]
