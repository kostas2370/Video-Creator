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
                    ("NONE", "None"),
                    ("AUTO", "Auto"),
                    ("ZOOM_IN", "Zoom In"),
                    ("ZOOM_OUT", "Zoom Out"),
                    ("PAN_LEFT", "Pan Left"),
                    ("PAN_RIGHT", "Pan Right"),
                    ("PAN_UP", "Pan Up"),
                    ("PAN_DOWN", "Pan Down"),
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
