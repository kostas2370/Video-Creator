from datetime import timedelta
from uuid import NAMESPACE_URL, uuid5

from django.db import migrations
from django.utils import timezone


UPDATES = [
    (
        "recurring-series",
        "One world. More stories. Meet series.",
        "Create a series around a recurring cast, a topic, or a world you want to "
        "keep exploring. Save your style and character references, then give each "
        "episode a new idea.\n\n"
        "Review the storyboard before generating media. Finished episodes add "
        "story memory for future episodes, while changes to your series setup "
        "apply to new episodes. References guide the look; generated results "
        "can still vary.\n\n"
        "Choose Create a series from Create to build your cast and start episode one.",
    ),
    (
        "spoken-video-highlights",
        "Give a long conversation a shorter cut",
        "Turn an interview, podcast, or talk into portrait clips with Long video "
        "→ Shorts. Upload a video or use a supported public YouTube link, then "
        "review the transcript and suggested highlights.\n\n"
        "Use Transcript & AI search to find another moment, or add a clip manually. "
        "Adjust its trim, framing, and captions before exporting. Each project "
        "supports up to 20 clips, each up to 180 seconds long.\n\n"
        "AI suggestions use your configured text provider. When suitable source "
        "captions are unavailable, transcription requires your OpenAI key. "
        "YouTube imports depend on source availability; uploading your own file "
        "is an alternative.",
    ),
    (
        "storyboard-revisions",
        "Shape the story before you generate the scenes",
        "Review your storyboard's narration and visual prompts before committing "
        "to media generation. Change the wording yourself or use Revise storyboard "
        "with AI to try a different direction.\n\n"
        "Review a suggested revision before applying it. Your current storyboard "
        "stays in place until you accept the changes. AI revisions use your "
        "connected provider and may incur usage charges.\n\n"
        "Try a short project first: adjust the opening, check the scene order, "
        "then generate when the story feels right.",
    ),
    (
        "narration-and-captions",
        "Start with your words or the footage you already have",
        "Narration to video accepts a script or a spoken MP3 or WAV recording "
        "and creates editable scenes around it. Review the visuals, timing, "
        "and narration before your final export.\n\n"
        "Already have a video? Use Add captions to create captions, then adjust "
        "the words, timing, and appearance. Audio transcription requires your "
        "OpenAI key.\n\n"
        "For a project without AI generation, choose Edit your own media and "
        "bring your photos, clips, and recorded audio. No provider key is needed "
        "for that manual workflow.",
    ),
]


def seed_updates(apps, schema_editor):
    updates = apps.get_model("news", "NewsUpdate").objects.using(
        schema_editor.connection.alias
    )
    published_at = timezone.now()
    for index, (slug, title, content) in enumerate(UPDATES):
        updates.get_or_create(
            pk=uuid5(NAMESPACE_URL, f"https://viddiecreator.com/news/{slug}"),
            defaults={
                "title": title,
                "content": content,
                "status": "PUBLISHED",
                "published_at": published_at - timedelta(microseconds=index),
            },
        )


class Migration(migrations.Migration):
    dependencies = [("news", "0003_seed_hosted_beta_news")]
    operations = [migrations.RunPython(seed_updates, migrations.RunPython.noop)]
