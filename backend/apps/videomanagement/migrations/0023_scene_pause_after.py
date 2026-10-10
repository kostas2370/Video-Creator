from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('videomanagement', '0022_scene_transition_duration_and_more')]
    operations = [migrations.AddField(model_name='scene', name='pause_after', field=models.FloatField(default=0))]
