from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("videomanagement", "0044_video_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="scene",
            name="shot_plan",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
