from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("videomanagement", "0041_templateprompt_ai_scene_editing")]

    operations = [
        migrations.AddField(
            model_name="scene",
            name="archived_at",
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
    ]
