from django.db import migrations


def move_content_type(apps, schema_editor, source, destination):
    # Preserve IDs so permissions, user/group grants and admin history survive.
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.using(schema_editor.connection.alias).filter(
        app_label=source, model="aiusage"
    ).update(app_label=destination)


def forwards(apps, schema_editor):
    move_content_type(apps, schema_editor, "videomanagement", "usage")


def backwards(apps, schema_editor):
    move_content_type(apps, schema_editor, "usage", "videomanagement")


class Migration(migrations.Migration):
    dependencies = [
        ("usage", "0001_initial"),
        ("videomanagement", "0052_move_usage_to_own_app"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [migrations.RunPython(forwards, backwards)]
