from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("apikeysmanagement", "0011_video_provider_keys")]

    operations = [
        migrations.AddField(
            model_name="apikeys",
            name="openai_warning",
            field=models.CharField(
                blank=True, db_default="", default="", editable=False, max_length=20
            ),
        ),
    ]
