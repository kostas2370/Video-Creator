from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("videomanagement", "0051_scene_starting_asset_scene_starting_image_context"),
        ("usage", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[migrations.DeleteModel(name="AIUsage")],
        ),
    ]
