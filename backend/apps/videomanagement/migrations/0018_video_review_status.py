from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("videomanagement", "0017_rename_openai_image_provider")]
    operations = [
        migrations.AlterField(
            model_name="video", name="status",
            field=models.CharField(
                max_length=20, default="RENDERING",
                choices=[(value, value) for value in
                         ("GENERATION", "REVIEW", "READY", "RENDERING", "COMPLETED", "FAILED")],
            ),
        ),
    ]
