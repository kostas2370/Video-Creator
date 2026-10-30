from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("videomanagement", "0049_move_series_to_own_app")]

    operations = [
        migrations.AddField(
            model_name="music",
            name="youtube_video_id",
            field=models.CharField(blank=True, db_index=True, max_length=11),
        ),
    ]
