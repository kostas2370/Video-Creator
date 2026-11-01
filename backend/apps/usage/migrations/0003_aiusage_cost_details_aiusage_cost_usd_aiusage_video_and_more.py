import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("usage", "0002_move_content_type"),
        ("videomanagement", "0052_move_usage_to_own_app"),
    ]

    operations = [
        migrations.AddField(
            model_name="aiusage",
            name="cost_details",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="aiusage",
            name="cost_usd",
            field=models.DecimalField(decimal_places=8, max_digits=16, null=True),
        ),
        migrations.AddField(
            model_name="aiusage",
            name="video",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="ai_usage",
                to="videomanagement.video",
            ),
        ),
        migrations.CreateModel(
            name="GenerationEstimate",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("estimate", models.JSONField(default=dict)),
                (
                    "video",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="videomanagement.video",
                    ),
                ),
            ],
        ),
    ]
