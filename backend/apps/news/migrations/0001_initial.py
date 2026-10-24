from uuid import uuid4

from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="NewsUpdate",
            fields=[
                ("id", models.UUIDField(default=uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(default=timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=200)),
                ("content", models.TextField(help_text="Plain text. Use blank lines between paragraphs.")),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("PUBLISHED", "Published")], default="DRAFT", max_length=10)),
                ("published_at", models.DateTimeField(default=timezone.now, help_text="Published entries become visible on this date. Future dates schedule an update.")),
            ],
            options={
                "ordering": ["-published_at", "-id"],
                "indexes": [models.Index(fields=["status", "published_at"], name="news_publication_idx")],
            },
        ),
    ]
