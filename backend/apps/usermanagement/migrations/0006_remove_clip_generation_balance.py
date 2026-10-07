from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("usermanagement", "0005_unique_login_user_ip"),
    ]

    operations = [
        migrations.RemoveField(model_name="user", name="generation_limit_for_twitch"),
    ]
