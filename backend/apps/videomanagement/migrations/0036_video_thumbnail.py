from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("videomanagement", "0035_video_tags")]
    operations = [
        migrations.AddField(
            model_name="video",
            name="thumbnail",
            field=models.ImageField(blank=True, upload_to="media/thumbnails/%Y/%m/%d"),
        ),
    ]
