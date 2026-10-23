from datetime import datetime
from uuid import NAMESPACE_URL, uuid5

from django.db import migrations
from django.utils import timezone


# Historical announcements use their merged release times. The guide/news entry
# is dated when this feature is installed in the workspace.
UPDATES = [
    (
        "guide-and-product-news",
        "A guide for your next video, and a place for product news",
        "The new Guide walks through choosing a creation tool, connecting providers, "
        "editing scenes, previewing, exporting, and publishing. It also covers common "
        "processing and narration issues.\n\n"
        "What’s New now brings product announcements together in one place. "
        "Both pages are available from Resources and the footer, including before sign-in.",
        None,
    ),
    (
        "faster-repeat-exports",
        "Faster exports when you revisit an edit",
        "Small projects without dissolves can render directly, avoiding temporary scene "
        "videos. When scene caching is enabled, later exports can reuse unchanged scene "
        "clips while applying your latest captions, overlays, and audio.\n\n"
        "Replacing a source file invalidates the affected cached visuals, so a new "
        "export uses the updated media.",
        "2026-10-23T14:03:18+03:00",
    ),
    (
        "faster-editor-loading",
        "A lighter editor and faster page loading",
        "Pages and media previews load as you need them, reducing the work needed "
        "to open the workspace. Scene media is deferred until needed, and fewer "
        "unnecessary requests are made while you browse and edit.\n\n"
        "Continue creating with AI, a story over gameplay, your own footage, or captions "
        "from the Create page.",
        "2026-10-23T12:39:08+03:00",
    ),
    (
        "video-details-before-publishing",
        "Review video details before publishing",
        "Edit your video’s title, description, and tags from the editor before "
        "publishing. You can review suggested descriptions and tags, adjust the "
        "wording, and save the details with your project.\n\n"
        "Your finished export stays available while you prepare its publishing details.",
        "2026-10-23T11:43:21+03:00",
    ),
    (
        "manage-publishing-connections",
        "Your publishing accounts, together in Connections",
        "Open Connections from the account menu to manage supported social accounts. "
        "Check connection status, reconnect an expired account, or disconnect one "
        "you no longer use.\n\n"
        "Available publishing platforms depend on your workspace configuration.",
        "2026-10-22T16:50:27+03:00",
    ),
    (
        "undo-and-scene-recovery",
        "Recover a scene and pick up where you left off",
        "Use Undo for recent scene edits and Recently deleted to restore removed "
        "scenes. The editor also remembers your selected scene and expanded panels "
        "so you can return to your work with less setup.",
        "2026-10-22T16:02:34+03:00",
    ),
]


def seed_updates(apps, schema_editor):
    NewsUpdate = apps.get_model("videomanagement", "NewsUpdate")
    updates = NewsUpdate.objects.using(schema_editor.connection.alias)
    for slug, title, content, released_at in UPDATES:
        updates.get_or_create(
            pk=uuid5(NAMESPACE_URL, f"https://viddie.app/news/{slug}"),
            defaults={
                "title": title,
                "content": content,
                "status": "PUBLISHED",
                "published_at": datetime.fromisoformat(released_at)
                if released_at else timezone.now(),
            },
        )


class Migration(migrations.Migration):
    dependencies = [("videomanagement", "0045_news_update")]
    operations = [migrations.RunPython(seed_updates, migrations.RunPython.noop)]
