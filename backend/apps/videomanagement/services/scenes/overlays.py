from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from apps.videomanagement.models import Scene
from apps.videomanagement.services.scenes.editing import changed, editable_video


def update_overlays(scene, data):
    with editable_video(scene.video_id) as video:
        scene = get_object_or_404(Scene.objects.select_for_update(), pk=scene.pk)
        if any(item["logo"] for item in data["overlays"]) and not (
            data.get("overlay_logo") or scene.overlay_logo
        ):
            raise ValidationError({"overlay_logo": "Upload a logo for the watermark."})
        scene.overlays = data["overlays"]
        fields = ["overlays"]
        if "overlay_logo" in data:
            scene.overlay_logo = data["overlay_logo"]
            fields.append("overlay_logo")
        scene.save(update_fields=fields)
        changed(video, invalidate_avatar=False)
    return scene
