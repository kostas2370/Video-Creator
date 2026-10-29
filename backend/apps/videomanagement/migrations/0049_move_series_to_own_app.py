from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("videomanagement", "0048_episode_memory_source"),
        ("series", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name="SeriesEpisode"),
                migrations.DeleteModel(name="VideoSeries"),
            ],
        ),
    ]
