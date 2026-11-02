"""Turn reviewed label plans into normal, editable overlays after media is ready."""

from django.db import transaction

from apps.videomanagement.models import Scene
from apps.videomanagement.schemas.scene_editing import PlannedOverlaySerializer
from apps.videomanagement.serializers.overlays import OverlaySerializer
from apps.videomanagement.utils.audio_editing import narration_enabled, narration_file
from apps.videomanagement.utils.file_utils import stored_file_exists
from apps.videomanagement.utils.timing import scene_timing


def apply_visual_plans(video):
    if not (video.settings or {}).get("ai_scene_editing"):
        return
    for scene_id in video.scenes.values_list("pk", flat=True):
        with transaction.atomic():
            scene = Scene.objects.select_for_update().select_related("video").with_media().get(pk=scene_id)
            shot_plan = dict(scene.shot_plan or {})
            plan = shot_plan.get("overlay_plan")
            if not plan or plan.get("applied"):
                continue
            # A resumed generation must preserve labels the user added themselves.
            if not scene.overlays:
                if narration_enabled(scene) and not stored_file_exists(narration_file(scene)):
                    continue
                labels = PlannedOverlaySerializer(data=plan["items"], many=True)
                labels.is_valid(raise_exception=True)
                image = next(iter(scene.scene_images.all()), None)
                duration = scene_timing(scene, image)["base_duration"]
                overlays = OverlaySerializer(data=[{
                    "kind": "title", "text": item["text"], "position": item["position"],
                    "start": item["start_fraction"] * duration,
                    "end": item["end_fraction"] * duration,
                } for item in labels.validated_data], many=True)
                overlays.is_valid(raise_exception=True)
                scene.overlays = list(overlays.validated_data)
            shot_plan["overlay_plan"] = {**plan, "applied": True}
            scene.shot_plan = shot_plan
            scene.save(update_fields=["overlays", "shot_plan"])
