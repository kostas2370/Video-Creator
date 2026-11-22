from uuid import NAMESPACE_URL, uuid5

from django.db import migrations
from django.utils import timezone


UPDATES = [
    (
        "hosted-beta",
        "The Viddie beta is live",
        "Viddie is now available at viddiecreator.com for invited accounts. Create a "
        "project, review and edit its scenes, then export a finished video.\n\n"
        "AI tools use the provider keys you save in API keys and providers. Connect "
        "the services you plan to use and check their model access and credit before "
        "generating. Talking presenters are disabled in this beta.\n\n"
        "The Guide now covers provider setup, music and icons, generation recovery, "
        "and sharing a finished export. Start with a short project while you explore.",
    ),
    (
        "beta-library-and-sharing",
        "Music, icons, and links to your finished videos",
        "Choose background music from Project extras and add icons from the scene "
        "controls. Preview and save your choices before exporting.\n\n"
        "Once an export is ready, use Share link to create a viewing link. Anyone "
        "with that link can watch without signing in. Set an expiry or revoke the "
        "link when you no longer want to share it. Your editor and provider keys "
        "remain private.",
    ),
]


def seed_updates(apps, schema_editor):
    updates = apps.get_model("news", "NewsUpdate").objects.using(
        schema_editor.connection.alias
    )
    published_at = timezone.now()
    for slug, title, content in UPDATES:
        updates.get_or_create(
            pk=uuid5(NAMESPACE_URL, f"https://viddiecreator.com/news/{slug}"),
            defaults={
                "title": title,
                "content": content,
                "status": "PUBLISHED",
                "published_at": published_at,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("news", "0002_seed_news_updates")]
    operations = [migrations.RunPython(seed_updates, migrations.RunPython.noop)]
