from uuid import uuid4

from django.db import migrations, models
from django.utils import timezone


def move_content_type(apps, schema_editor, source, target):
    ContentType = apps.get_model("contenttypes", "ContentType")
    types = ContentType.objects.using(schema_editor.connection.alias)
    if not types.filter(app_label=target, model="newsupdate").exists():
        # Keep the content type ID so existing admin permissions and log entries
        # continue to refer to the same model after changing its app label.
        types.filter(app_label=source, model="newsupdate").update(app_label=target)


def move_news_permissions(apps, schema_editor):
    move_content_type(apps, schema_editor, "videomanagement", "news")


def restore_news_permissions(apps, schema_editor):
    move_content_type(apps, schema_editor, "news", "videomanagement")


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("videomanagement", "0046_seed_news_updates"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]
    operations = [
        migrations.RunPython(move_news_permissions, restore_news_permissions),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
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
                        "db_table": "videomanagement_newsupdate",
                        "ordering": ["-published_at", "-id"],
                        "indexes": [models.Index(fields=["status", "published_at"], name="news_publication_idx")],
                    },
                ),
            ],
        ),
    ]
