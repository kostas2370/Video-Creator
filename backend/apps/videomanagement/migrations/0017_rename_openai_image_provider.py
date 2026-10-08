from django.db import migrations


def forwards(apps, schema_editor):
    alias = schema_editor.connection.alias
    apps.get_model("videomanagement", "TemplatePrompt").objects.using(alias).filter(
        provider="DALL-E"
    ).update(provider="OPENAI")
    videos = apps.get_model("videomanagement", "Video").objects.using(alias)
    for video in videos.filter(settings__provider="DALL-E").iterator():
        video.settings = {**video.settings, "provider": "OPENAI"}
        video.save(using=alias, update_fields=["settings"])


def backwards(apps, schema_editor):
    alias = schema_editor.connection.alias
    apps.get_model("videomanagement", "TemplatePrompt").objects.using(alias).filter(
        provider="OPENAI"
    ).update(provider="DALL-E")
    videos = apps.get_model("videomanagement", "Video").objects.using(alias)
    for video in videos.filter(settings__provider="OPENAI").iterator():
        video.settings = {**video.settings, "provider": "DALL-E"}
        video.save(using=alias, update_fields=["settings"])


class Migration(migrations.Migration):
    dependencies = [("videomanagement", "0016_templateprompt_scene_count")]

    operations = [migrations.RunPython(forwards, backwards)]
