from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("videomanagement", "0040_sceneimage_asset_owns_file")]

    operations = [
        migrations.AddField(
            model_name="templateprompt",
            name="ai_scene_editing",
            field=models.BooleanField(default=False),
        ),
    ]
