from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("apikeysmanagement", "0008_provider_timestamps"),
    ]

    operations = [
        migrations.RemoveField(model_name="apikeys", name="twitch_client_id"),
        migrations.RemoveField(model_name="apikeys", name="twitch_client_secret"),
    ]
