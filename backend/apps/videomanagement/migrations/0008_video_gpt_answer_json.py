import ast
import json

from django.db import migrations, models


def as_json_text(raw):
    try:
        json.loads(raw)
        return raw

    except (TypeError, ValueError):
        pass

    try:
        return json.dumps(ast.literal_eval(raw))

    except (TypeError, ValueError, SyntaxError, MemoryError, RecursionError):
        return json.dumps(raw)


def to_json(apps, schema_editor):
    Video = apps.get_model("videomanagement", "Video")

    for pk, raw in Video.objects.exclude(gpt_answer=None).values_list(
        "pk", "gpt_answer"
    ):
        converted = as_json_text(raw)
        if converted != raw:
            Video.objects.filter(pk=pk).update(gpt_answer=converted)


def to_text(apps, schema_editor):
    Video = apps.get_model("videomanagement", "Video")

    for pk, value in Video.objects.exclude(gpt_answer=None).values_list(
        "pk", "gpt_answer"
    ):
        if isinstance(value, str):
            Video.objects.filter(pk=pk).update(gpt_answer=value)


class Migration(migrations.Migration):
    dependencies = [
        ("videomanagement", "0007_alter_templateprompt_title_and_more"),
    ]

    operations = [
        migrations.RunPython(to_json, to_text),
        migrations.AlterField(
            model_name="video",
            name="gpt_answer",
            field=models.JSONField(blank=True, null=True),
        ),
    ]
