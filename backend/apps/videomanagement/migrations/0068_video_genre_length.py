from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('videomanagement', '0067_video_generation_error'),
    ]

    operations = [
        migrations.AlterField(
            model_name='video',
            name='genre',
            field=models.CharField(blank=True, null=True, max_length=50),
        ),
    ]
