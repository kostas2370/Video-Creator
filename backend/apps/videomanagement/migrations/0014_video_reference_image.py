from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("videomanagement", "0013_templateprompt_platform")]

    operations = [
        migrations.AddField(
            model_name="video",
            name="reference_image",
            field=models.ImageField(upload_to="media/references/%Y/%m/%d", blank=True),
        ),
    ]
