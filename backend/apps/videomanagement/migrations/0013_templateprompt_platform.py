from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("videomanagement", "0012_templateprompt_video_format"),
    ]

    operations = [
        migrations.AddField(
            model_name="templateprompt",
            name="platform",
            field=models.CharField(
                choices=[("GENERAL", "General video"), ("TIKTOK", "TikTok")],
                default="GENERAL",
                max_length=12,
            ),
        ),
    ]
