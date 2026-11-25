from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("apikeysmanagement", "0010_alter_usercustomvisualprovider_options")
    ]
    operations = [
        migrations.AddField(
            model_name="apikeys",
            name="fal_key",
            field=models.TextField(max_length=255, blank=True, default=""),
        ),
        migrations.AddField(
            model_name="apikeys",
            name="runway_key",
            field=models.TextField(max_length=255, blank=True, default=""),
        ),
    ]
