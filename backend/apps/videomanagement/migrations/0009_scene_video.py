import django.db.models.deletion
from django.db import migrations, models


def prompt_to_video(apps, schema_editor):
    Scene = apps.get_model("videomanagement", "Scene")
    Video = apps.get_model("videomanagement", "Video")

    videos = dict(Video.objects.values_list("prompt_id", "pk"))
    orphaned = 0

    for pk, prompt_id in Scene.objects.values_list("pk", "prompt_id"):
        video_id = videos.get(prompt_id)
        if video_id is None:
            orphaned += 1
            continue

        Scene.objects.filter(pk=pk).update(video_id=video_id)

    Scene.objects.filter(video__isnull=True).delete()
    if orphaned:
        print(f"  dropped {orphaned} scenes that belonged to no video")


def video_to_prompt(apps, schema_editor):
    Scene = apps.get_model("videomanagement", "Scene")

    for pk, prompt_id in Scene.objects.values_list("pk", "video__prompt_id"):
        Scene.objects.filter(pk=pk).update(prompt_id=prompt_id)


class Migration(migrations.Migration):
    dependencies = [
        ("videomanagement", "0008_video_gpt_answer_json"),
    ]

    operations = [
        migrations.AddField(
            model_name="scene",
            name="video",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="scenes",
                to="videomanagement.video",
            ),
        ),
        migrations.RunPython(prompt_to_video, video_to_prompt),
        migrations.AlterField(
            model_name="scene",
            name="video",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="scenes",
                to="videomanagement.video",
            ),
        ),
        migrations.RemoveField(
            model_name="scene",
            name="prompt",
        ),
    ]
