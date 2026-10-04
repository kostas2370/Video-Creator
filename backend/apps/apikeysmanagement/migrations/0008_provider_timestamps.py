from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):
    dependencies = [
        ("apikeysmanagement", "0007_usercustomttsprovider_extra_parameters_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="usercustomttsprovider",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="usercustomttsprovider",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="usercustomttsprovider",
            name="endpoint_url",
            field=models.URLField(max_length=500),
        ),
    ]
