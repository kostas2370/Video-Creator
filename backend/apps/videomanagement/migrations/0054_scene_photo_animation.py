from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("videomanagement", "0053_update_script_model_catalog")]

    operations = [
        migrations.AddField(
            model_name="scene", name="animation_preset",
            field=models.CharField(
                max_length=10, default="NONE",
                choices=[("NONE", "None"), ("PLAYFUL", "Playful"),
                         ("DRAMATIC", "Dramatic"), ("CALM", "Calm"),
                         ("EXPLAINER", "Explainer")],
            ),
        ),
        migrations.AddField(
            model_name="scene", name="animation_accents",
            field=models.BooleanField(default=True),
        ),
    ]
