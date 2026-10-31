from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("series", "0002_move_content_types")]

    operations = [
        migrations.AddField(
            model_name="videoseries",
            name="cast",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="videoseries",
            name="story_format",
            field=models.CharField(
                choices=[
                    ("GENERAL", "General series"),
                    ("ANIMATED_STORY", "Animated character story"),
                    ("SERIAL_DRAMA", "Serial drama"),
                ],
                default="GENERAL",
                max_length=20,
            ),
        ),
    ]
