from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("videomanagement", "0026_scene_audio")]
    operations = [
        migrations.AlterField(model_name="video", name="video_type", field=models.CharField(
            max_length=20, default="AI", choices=[("AI", "AI"), ("MANUAL", "Manual")])),
    ]
