from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("videomanagement", "0056_icon_owner")]

    operations = [
        migrations.AddField(
            model_name="video",
            name="operation_id",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.AddField(
            model_name="video",
            name="narration_retry_status",
            field=models.CharField(
                blank=True, db_default="", default="", editable=False, max_length=12
            ),
        ),
    ]
