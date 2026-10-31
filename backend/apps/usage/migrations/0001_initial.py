# Adopt the existing usage table without recreating or copying records.

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("videomanagement", "0051_scene_starting_asset_scene_starting_image_context"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="AIUsage",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                        (
                            "service",
                            models.CharField(
                                choices=[
                                    ("text", "Text"),
                                    ("images", "Images"),
                                    ("tts", "Voice"),
                                    ("video", "Video"),
                                    ("stt", "Transcription"),
                                ],
                                max_length=10,
                            ),
                        ),
                        ("provider", models.CharField(max_length=100)),
                        ("model", models.CharField(blank=True, max_length=100)),
                        ("key_source", models.CharField(max_length=10)),
                        ("input_tokens", models.PositiveBigIntegerField(null=True)),
                        ("output_tokens", models.PositiveBigIntegerField(null=True)),
                        ("total_tokens", models.PositiveBigIntegerField(null=True)),
                        ("characters", models.PositiveBigIntegerField(default=0)),
                        ("images", models.PositiveIntegerField(default=0)),
                        ("seconds", models.PositiveIntegerField(default=0)),
                        (
                            "user",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                    ],
                    options={
                        "db_table": "videomanagement_aiusage",
                        "indexes": [
                            models.Index(
                                fields=["user", "created_at"], name="ai_usage_user_date"
                            )
                        ],
                    },
                ),
            ],
        ),
    ]
