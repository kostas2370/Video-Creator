from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("videomanagement", "0046_seed_news_updates"),
        ("news", "0001_initial"),
    ]
    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[migrations.DeleteModel(name="NewsUpdate")],
        ),
    ]
