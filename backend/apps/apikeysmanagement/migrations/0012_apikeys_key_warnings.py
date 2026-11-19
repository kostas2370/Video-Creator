from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("apikeysmanagement", "0011_video_provider_keys")]

    operations = [
        migrations.AddField(
            model_name="apikeys",
            name="key_warnings",
            field=models.JSONField(
                blank=True, db_default={}, default=dict, editable=False
            ),
        ),
    ]
