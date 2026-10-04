from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("videomanagement", "0011_normalize_tts_provider_names"),
    ]

    operations = [
        migrations.AddField(
            model_name="video",
            name="dispatch_token",
            field=models.UUIDField(editable=False, null=True),
        ),
    ]
