from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("videomanagement", "0034_media_library_and_covers")]
    operations = [
        migrations.AddField(
            model_name="video",
            name="tags",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
