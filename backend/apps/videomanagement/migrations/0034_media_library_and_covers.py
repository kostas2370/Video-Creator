from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):
    dependencies = [("videomanagement", "0033_video_notes"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.AddField(model_name="video", name="cover", field=models.ImageField(blank=True, upload_to="media/covers/%Y/%m/%d")),
        migrations.AddField(model_name="video", name="cover_settings", field=models.JSONField(blank=True, default=dict)),
        migrations.CreateModel(name="MediaAsset", fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ("title", models.CharField(max_length=100)),
            ("file", models.FileField(max_length=255, upload_to="media/library/%Y/%m/%d")),
            ("kind", models.CharField(choices=[("IMAGE", "Image"), ("VIDEO", "Video"), ("AUDIO", "Audio")], max_length=10)),
            ("tags", models.JSONField(blank=True, default=list)),
            ("duration", models.FloatField(blank=True, null=True)),
            ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
            ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
        ], options={"ordering": ["-created_at", "-id"]}),
    ]
