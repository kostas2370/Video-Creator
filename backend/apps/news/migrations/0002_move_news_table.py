from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("news", "0001_initial"),
        ("videomanagement", "0047_move_news_to_own_app"),
    ]
    operations = [migrations.AlterModelTable(name="newsupdate", table=None)]
