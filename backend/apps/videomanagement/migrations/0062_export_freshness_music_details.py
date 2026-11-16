from django.db import migrations, models
import django.db.models.deletion


def link_catalog_music(apps, schema_editor):
    Music = apps.get_model("videomanagement", "Music")
    Track = apps.get_model("videomanagement", "MusicCatalogTrack")
    database = schema_editor.connection.alias
    for track in (
        Track.objects.using(database)
        .filter(source_id__startswith="youtube:")
        .iterator()
    ):
        Music.objects.using(database).filter(
            youtube_video_id=track.source_id[8:]
        ).exclude(youtube_video_id="").update(catalog_track=track)


class Migration(migrations.Migration):
    dependencies = [("videomanagement", "0061_merge_music_catalog_and_video_cuts")]
    operations = [
        migrations.AddField(
            model_name="video",
            name="export_source_key",
            field=models.CharField(max_length=64, blank=True, editable=False),
        ),
        migrations.AddField(
            model_name="video",
            name="exported_at",
            field=models.DateTimeField(null=True, blank=True, editable=False),
        ),
        migrations.AddField(
            model_name="music",
            name="catalog_track",
            field=models.ForeignKey(
                to="videomanagement.musiccatalogtrack",
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.SET_NULL,
            ),
        ),
        migrations.RunPython(link_catalog_music, migrations.RunPython.noop),
    ]
