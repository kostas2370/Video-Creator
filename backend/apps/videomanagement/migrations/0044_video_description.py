from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("videomanagement", "0043_scene_recovery_retention")]
    operations = [
        migrations.AddField(
            model_name="video",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
    ]
