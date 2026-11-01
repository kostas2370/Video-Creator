from django.db import migrations, models


REPLACEMENTS = {
    "claude-3-5-sonnet-20240620": "claude-sonnet-5-5",
    "gemini-1.5-pro": "gemini-4-argon",
    "gemini-1.5-flash": "gemini-3.8-flash",
    "gemini-1.0-pro": "gemini-3.5-flash-lite",
}


def replace_saved_models(apps, schema_editor):
    alias = schema_editor.connection.alias
    templates = apps.get_model("videomanagement", "TemplatePrompt").objects.using(alias)
    for old, new in REPLACEMENTS.items():
        templates.filter(gpt_model=old).update(gpt_model=new)
    videos = apps.get_model("videomanagement", "Video").objects.using(alias)
    for video in videos.only("pk", "settings").iterator(chunk_size=200):
        settings = video.settings
        if not isinstance(settings, dict):
            continue
        params = settings.get("generation_params")
        if isinstance(params, dict) and params.get("gpt_model") in REPLACEMENTS:
            videos.filter(pk=video.pk).update(
                settings={
                    **settings,
                    "generation_params": {
                        **params,
                        "gpt_model": REPLACEMENTS[params["gpt_model"]],
                    },
                }
            )


class Migration(migrations.Migration):
    dependencies = [
        ("videomanagement", "0052_move_usage_to_own_app"),
    ]

    operations = [
        migrations.RunPython(replace_saved_models, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="templateprompt",
            name="gpt_model",
            field=models.CharField(
                blank=True,
                choices=[
                    ("gpt-3.5-turbo", "gpt-3.5-turbo"),
                    ("gpt-4", "gpt-4"),
                    ("gpt-4-turbo", "gpt-4-turbo"),
                    ("gpt-4o", "gpt-4o"),
                    ("gpt-4o-mini", "gpt-4o-mini"),
                    ("gpt-4.1", "gpt-4.1"),
                    ("gpt-4.1-mini", "gpt-4.1-mini"),
                    ("gpt-4.1-nano", "gpt-4.1-nano"),
                    ("gpt-5", "gpt-5"),
                    ("gpt-5-mini", "gpt-5-mini"),
                    ("gpt-5-nano", "gpt-5-nano"),
                    ("gpt-5-chat-latest", "gpt-5-chat-latest"),
                    ("gpt-5.1", "gpt-5.1"),
                    ("gpt-5.1-chat-latest", "gpt-5.1-chat-latest"),
                    ("gpt-5.2", "gpt-5.2"),
                    ("gpt-5.2-chat-latest", "gpt-5.2-chat-latest"),
                    ("gpt-5.3-chat-latest", "gpt-5.3-chat-latest"),
                    ("gpt-5.4", "gpt-5.4"),
                    ("gpt-5.4-mini", "gpt-5.4-mini"),
                    ("gpt-5.4-nano", "gpt-5.4-nano"),
                    ("gpt-5.5", "gpt-5.5"),
                    ("gpt-5.6-luna", "gpt-5.6-luna"),
                    ("gpt-5.6-sol", "gpt-5.6-sol"),
                    ("gpt-5.6-terra", "gpt-5.6-terra"),
                    ("gpt-6-astra", "gpt-6-astra"),
                    ("o1", "o1"),
                    ("o3", "o3"),
                    ("o3-mini", "o3-mini"),
                    ("o4-mini", "o4-mini"),
                    ("claude-sonnet-5-5", "claude-sonnet-5-5"),
                    ("gemini-4-argon", "gemini-4-argon"),
                    ("gemini-3.8-flash", "gemini-3.8-flash"),
                    ("gemini-3.5-flash-lite", "gemini-3.5-flash-lite"),
                ],
                default="gpt-5.4-mini",
                max_length=50,
            ),
        ),
    ]
