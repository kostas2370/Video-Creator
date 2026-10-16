from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("videomanagement", "0028_ai_usage")]
    operations = [
        migrations.AddField(
            model_name="scene",
            name="overlays",
            field=models.JSONField(default=list, blank=True),
        ),
        migrations.AddField(
            model_name="scene",
            name="overlay_logo",
            field=models.ImageField(upload_to="media/overlays/%Y/%m/%d", blank=True),
        ),
    ]
