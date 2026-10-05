from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("videomanagement", "0013_templateprompt_platform")]

    operations = [
        migrations.CreateModel(
            name="SceneCreationJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(default="QUEUED", max_length=20)),
                ("data", models.JSONField(default=dict)),
                ("upload", models.FileField(blank=True, max_length=2000, upload_to="media/scene_uploads")),
                ("error", models.TextField(blank=True, default="")),
                ("previous_status", models.CharField(default="READY", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("video", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="scene_jobs", to="videomanagement.video")),
            ],
        ),
    ]
