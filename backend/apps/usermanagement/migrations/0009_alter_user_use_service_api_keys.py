import apps.usermanagement.models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("usermanagement", "0008_remove_generation_credit_balance")]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="use_service_api_keys",
            field=models.BooleanField(
                default=apps.usermanagement.models.default_service_api_keys
            ),
        ),
    ]
