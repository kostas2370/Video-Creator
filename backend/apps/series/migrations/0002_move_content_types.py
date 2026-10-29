from django.db import migrations


def move_content_types(apps, schema_editor, source, destination):
    # Keep primary keys so permissions, user/group grants and admin history survive.
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.using(schema_editor.connection.alias).filter(
        app_label=source, model__in=("videoseries", "seriesepisode")
    ).update(app_label=destination)


def forwards(apps, schema_editor):
    move_content_types(apps, schema_editor, "videomanagement", "series")


def backwards(apps, schema_editor):
    move_content_types(apps, schema_editor, "series", "videomanagement")


class Migration(migrations.Migration):
    dependencies = [
        ("series", "0001_initial"),
        ("videomanagement", "0049_move_series_to_own_app"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [migrations.RunPython(forwards, backwards)]
