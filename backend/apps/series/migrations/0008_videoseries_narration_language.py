from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("series", "0007_videoseries_generation_mode")]
    operations = [
        migrations.AddField(
            model_name="videoseries",
            name="narration_language",
            field=models.CharField(max_length=80, blank=True, default=""),
        )
    ]
