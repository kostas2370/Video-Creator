from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("clips", "0009_clipproject_transcript_source")]
    operations = [
        migrations.AddField(
            model_name="clip",
            name="segments",
            field=models.JSONField(default=list, blank=True),
        )
    ]
