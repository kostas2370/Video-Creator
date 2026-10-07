from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("videomanagement", "0014_video_reference_image"),
    ]

    operations = [
        migrations.AlterField(
            model_name="video",
            name="video_type",
            field=models.CharField(choices=[("AI", "AI")], default="AI", max_length=20),
        ),
    ]
