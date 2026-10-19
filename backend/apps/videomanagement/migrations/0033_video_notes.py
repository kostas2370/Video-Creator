from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("videomanagement", "0031_caption_projects")]

    operations = [
        migrations.AddField(
            model_name="video", name="notes",
            field=models.TextField(blank=True, default="", max_length=10000),
        ),
    ]
