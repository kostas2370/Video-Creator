from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("apikeysmanagement", "0011_video_provider_keys")]

    operations = [
        migrations.CreateModel(
            name="ProviderKeyWarning",
            fields=[
                (
                    "fingerprint",
                    models.CharField(max_length=64, primary_key=True, serialize=False),
                ),
                ("code", models.CharField(max_length=20)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
