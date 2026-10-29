# Adopt the existing series tables without changing their data or schema.

import uuid

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("videomanagement", "0048_episode_memory_source"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    initial = True

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="VideoSeries",
                    fields=[
                        (
                            "id",
                            models.UUIDField(
                                default=uuid.uuid4,
                                editable=False,
                                primary_key=True,
                                serialize=False,
                            ),
                        ),
                        (
                            "created_at",
                            models.DateTimeField(default=django.utils.timezone.now),
                        ),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                        ("title", models.CharField(max_length=100)),
                        ("premise", models.TextField(max_length=2000)),
                        ("characters", models.TextField(blank=True, max_length=2000)),
                        ("visual_style", models.TextField(max_length=800)),
                        (
                            "reference_image",
                            models.ImageField(
                                blank=True, upload_to="media/series/%Y/%m/%d"
                            ),
                        ),
                        (
                            "provider",
                            models.CharField(default="OPENAI", max_length=100),
                        ),
                        ("narration", models.BooleanField(default=True)),
                        ("subtitles", models.BooleanField(default=True)),
                        (
                            "video_format",
                            models.CharField(
                                choices=[
                                    ("LANDSCAPE", "Landscape (16:9)"),
                                    ("PORTRAIT", "Portrait (9:16)"),
                                    ("SQUARE", "Square (1:1)"),
                                ],
                                default="PORTRAIT",
                                max_length=12,
                            ),
                        ),
                        (
                            "platform",
                            models.CharField(
                                choices=[
                                    ("GENERAL", "General video"),
                                    ("TIKTOK", "TikTok"),
                                ],
                                default="GENERAL",
                                max_length=12,
                            ),
                        ),
                        (
                            "scene_count",
                            models.PositiveSmallIntegerField(
                                default=6,
                                validators=[
                                    django.core.validators.MinValueValidator(1),
                                    django.core.validators.MaxValueValidator(60),
                                ],
                            ),
                        ),
                        (
                            "created_by",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.CASCADE,
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                        (
                            "intro",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                to="videomanagement.intro",
                            ),
                        ),
                        (
                            "outro",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                to="videomanagement.outro",
                            ),
                        ),
                        (
                            "voice_model",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                to="videomanagement.voicemodel",
                            ),
                        ),
                    ],
                    options={
                        "ordering": ["-updated_at", "id"],
                        "db_table": "videomanagement_videoseries",
                    },
                ),
                migrations.CreateModel(
                    name="SeriesEpisode",
                    fields=[
                        (
                            "id",
                            models.UUIDField(
                                default=uuid.uuid4,
                                editable=False,
                                primary_key=True,
                                serialize=False,
                            ),
                        ),
                        (
                            "created_at",
                            models.DateTimeField(default=django.utils.timezone.now),
                        ),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                        (
                            "memory_source_hash",
                            models.CharField(blank=True, default="", max_length=64),
                        ),
                        ("is_canon", models.BooleanField(default=False)),
                        ("number", models.PositiveIntegerField()),
                        ("idea", models.TextField(max_length=2000)),
                        ("summary", models.TextField(blank=True, max_length=800)),
                        ("profile_snapshot", models.JSONField(default=dict)),
                        ("generation_params", models.JSONField(default=dict)),
                        (
                            "video",
                            models.OneToOneField(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                related_name="series_episode",
                                to="videomanagement.video",
                            ),
                        ),
                        (
                            "series",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="episodes",
                                to="series.videoseries",
                            ),
                        ),
                    ],
                    options={
                        "ordering": ["-number"],
                        "db_table": "videomanagement_seriesepisode",
                        "constraints": [
                            models.UniqueConstraint(
                                fields=("series", "number"),
                                name="unique_series_episode_number",
                            )
                        ],
                    },
                ),
            ]
        )
    ]
