from django.db import migrations


PROVIDER_NAMES = {
    "open_ai": "OPENAI",
    "eleven_labs": "ELEVENLABS",
    "60db": "SIXTYDB",
}


def rename_providers(apps, schema_editor, names):
    voices = apps.get_model("videomanagement", "VoiceModel").objects.using(
        schema_editor.connection.alias
    )
    for old_name, new_name in names.items():
        voices.filter(type="API", provider=old_name).update(provider=new_name)


def forwards(apps, schema_editor):
    rename_providers(apps, schema_editor, PROVIDER_NAMES)


def backwards(apps, schema_editor):
    rename_providers(
        apps, schema_editor, {new: old for old, new in PROVIDER_NAMES.items()}
    )


class Migration(migrations.Migration):
    dependencies = [
        ("videomanagement", "0010_alter_voicemodel_type"),
    ]

    operations = [migrations.RunPython(forwards, backwards)]
