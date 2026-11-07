from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("videomanagement", "0057_video_operation_id_narration_retry_status"),
    ]

    operations = [
        migrations.RenameField(
            model_name="scene",
            old_name="starting_image_context",
            new_name="starting_frame_context",
        ),
    ]
