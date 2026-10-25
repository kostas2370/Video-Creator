from django.db import migrations
from encrypted_model_fields.fields import EncryptedCharField


class Migration(migrations.Migration):
    dependencies = [
        ("apikeysmanagement", "0010_alter_usercustomvisualprovider_options")
    ]
    operations = [
        migrations.AddField(
            model_name="apikeys",
            name="fal_key",
            field=EncryptedCharField(max_length=255, blank=True, default=""),
        ),
        migrations.AddField(
            model_name="apikeys",
            name="runway_key",
            field=EncryptedCharField(max_length=255, blank=True, default=""),
        ),
    ]
