from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("videomanagement", "0062_export_freshness_music_details")]
    operations = [
        migrations.AddField(
            model_name="templateprompt",
            name="narration_language",
            field=models.CharField(max_length=80, blank=True, default=""),
        )
    ]
