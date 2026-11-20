import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("videomanagement", "0068_video_genre_length")]

    operations = [
        migrations.CreateModel(
            name="VideoShare",
            fields=[
                (
                    "token",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                (
                    "video",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="public_share",
                        to="videomanagement.video",
                    ),
                ),
            ],
        ),
    ]
