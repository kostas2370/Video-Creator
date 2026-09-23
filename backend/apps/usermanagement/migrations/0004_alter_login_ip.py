from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("usermanagement", "0003_notification_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="login",
            name="ip",
            field=models.GenericIPAddressField(),
        ),
    ]
