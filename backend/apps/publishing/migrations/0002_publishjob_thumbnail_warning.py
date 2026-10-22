import apps.publishing.storage
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("publishing", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="publishjob",
            name="thumbnail",
            field=models.FileField(blank=True, max_length=2000, storage=apps.publishing.storage.PrivateExportStorage(), upload_to="thumbnails/%Y/%m/%d"),
        ),
        migrations.AddField(
            model_name="publishjob",
            name="warning",
            field=models.CharField(blank=True, max_length=500),
        ),
    ]
