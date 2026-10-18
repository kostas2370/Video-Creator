from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("videomanagement", "0028_ai_usage")]

    operations = [
        migrations.AddField(model_name="voicemodel", name="is_cloned", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="voicemodel", name="clone_key_source", field=models.CharField(blank=True, max_length=10)),
        migrations.AddField(model_name="voicemodel", name="clone_key_fingerprint", field=models.CharField(blank=True, max_length=64)),
        migrations.AddField(model_name="voicemodel", name="consented_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="voicemodel", name="requires_verification", field=models.BooleanField(default=False)),
    ]
