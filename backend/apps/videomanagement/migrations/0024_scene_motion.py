from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("videomanagement", "0023_scene_pause_after")]
    operations = [
        migrations.AddField(
            model_name="scene",
            name="motion_style",
            field=models.CharField(
                max_length=10,
                choices=[
                    (value, value.replace("_", " ").title())
                    for value in (
                        "NONE",
                        "AUTO",
                        "ZOOM_IN",
                        "ZOOM_OUT",
                        "PAN_LEFT",
                        "PAN_RIGHT",
                        "PAN_UP",
                        "PAN_DOWN",
                    )
                ],
                default="NONE",
            ),
        ),
        migrations.AddField(
            model_name="scene",
            name="motion_intensity",
            field=models.CharField(
                max_length=6,
                choices=[
                    ("SUBTLE", "Subtle"),
                    ("MEDIUM", "Medium"),
                    ("STRONG", "Strong"),
                ],
                default="SUBTLE",
            ),
        ),
    ]
