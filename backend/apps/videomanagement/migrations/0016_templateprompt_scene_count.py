import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("videomanagement", "0015_restrict_video_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="templateprompt",
            name="scene_count",
            field=models.PositiveSmallIntegerField(
                blank=True, null=True,
                validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(60)],
            ),
        ),
    ]
