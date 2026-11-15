from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("series", "0006_single_character")]

    operations = [
        migrations.AddField(
            model_name="videoseries",
            name="generation_mode",
            field=models.CharField(
                choices=[("STANDARD", "Standard"), ("ECONOMY", "Economy")],
                default="STANDARD",
                max_length=12,
            ),
        ),
    ]
