from django.db import migrations, models
from django.db.models import Count, Min, Sum


def merge_duplicate_logins(apps, schema_editor):
    logins = apps.get_model("usermanagement", "Login").objects.using(
        schema_editor.connection.alias
    )
    duplicates = (
        logins.values("user_id", "ip")
        .annotate(
            row_count=Count("pk"),
            first_id=Min("pk"),
            total_count=Sum("count"),
            first_seen=Min("date"),
        )
        .filter(row_count__gt=1)
    )
    for group in duplicates.iterator():
        logins.filter(pk=group["first_id"]).update(
            count=group["total_count"], date=group["first_seen"]
        )
        logins.filter(user_id=group["user_id"], ip=group["ip"]).exclude(
            pk=group["first_id"]
        ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("usermanagement", "0004_alter_login_ip"),
    ]

    operations = [
        migrations.RunPython(merge_duplicate_logins, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="login",
            constraint=models.UniqueConstraint(
                fields=("user", "ip"), name="unique_login_user_ip"
            ),
        ),
    ]
