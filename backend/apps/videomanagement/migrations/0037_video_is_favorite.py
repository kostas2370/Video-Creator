from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("videomanagement", "0036_video_thumbnail")]

    operations = [
        migrations.AddField(
            model_name="video",
            name="is_favorite",
            field=models.BooleanField(default=False),
        ),
    ]
