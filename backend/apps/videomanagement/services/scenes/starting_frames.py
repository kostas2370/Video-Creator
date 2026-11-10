from rest_framework.exceptions import ValidationError

from apps.videomanagement.integrations.visuals import ImageProviderRegistry
from apps.videomanagement.models import ImageMode, SceneImage
from apps.videomanagement.services.scenes.editing import changed, editable_video
from apps.videomanagement.services.scenes.visuals import (
    planned_visual_prompt,
    generate_scene_visual,
    store_starting_frame,
    starting_frame_key,
    starting_frame_matches,
)
from apps.videomanagement.utils.file_utils import stored_file_exists


def requires_starting_frame(video):
    return bool(
        (video.settings or {}).get("character_references")
        and video.mode == ImageMode.AI
        and ImageProviderRegistry.is_video(
            (video.settings or {}).get("provider"),
            user=video.created_by,
            mode=video.mode,
        )
    )


def current_frame_key(scene, description, style):
    video = scene.video
    return starting_frame_key(
        video,
        planned_visual_prompt(
            scene, description, video.mode, (video.settings or {}).get("provider")
        ),
        style,
    )


def starting_frame_current(scene):
    context = scene.starting_frame_context or {}
    video = scene.video
    return starting_frame_matches(
        video,
        planned_visual_prompt(
            scene,
            context.get("description", ""),
            video.mode,
            (video.settings or {}).get("provider"),
        ),
        context.get("style", "natural"),
        context,
    )


def starting_frame_status(scene):
    context = scene.starting_frame_context or {}
    if not scene.starting_asset_id or not stored_file_exists(scene.starting_asset.file):
        return "missing"
    if not starting_frame_current(scene):
        return "needs_review"
    return (
        "approved"
        if context.get("approved_asset") == str(scene.starting_asset_id)
        else "needs_review"
    )


def validate_starting_frame_state(scene, asset_id):
    if not requires_starting_frame(scene.video):
        raise ValidationError(
            "Starting-frame review is available for character video shots."
        )
    if not ImageProviderRegistry.supports_reference(
        (scene.video.settings or {}).get("provider")
    ):
        raise ValidationError(
            "Choose a video provider with reference-image support for this cast."
        )
    if str(scene.starting_asset_id or "") != str(asset_id or ""):
        raise ValidationError(
            "The starting frame changed. Refresh and review it again."
        )


def validate_current_starting_frame(scene):
    if (
        scene.archived_at
        or not scene.starting_asset_id
        or not stored_file_exists(scene.starting_asset.file)
    ):
        raise ValidationError("Prepare a starting frame before reviewing or approving it.")
    if not starting_frame_current(scene):
        raise ValidationError(
            "The shot settings changed. Prepare and review a new starting frame."
        )


def _upload_starting_frame(scene, image, image_description):
    description = image_description or (scene.starting_frame_context or {}).get(
        "description", ""
    )
    if not description:
        raise ValidationError("Add a shot description before uploading a starting frame.")
    style = (scene.video.settings or {}).get("style", "natural")
    store_starting_frame(
        scene,
        image,
        description=description,
        style=style,
        key=current_frame_key(scene, description, style),
    )


def save_starting_frame(
    scene, *, operation, asset_id=None, image=None, image_description=None
):
    with editable_video(scene.video_id) as video:
        scene.refresh_from_db()
        scene.video = video
        validate_starting_frame_state(scene, asset_id)
        if operation == "upload":
            _upload_starting_frame(scene, image, image_description)
        elif operation == "approve":
            validate_current_starting_frame(scene)
            scene.starting_frame_context = {
                **(scene.starting_frame_context or {}),
                "approved_asset": str(scene.starting_asset_id),
            }
            scene.save(update_fields=["starting_frame_context"])
        else:
            raise ValidationError("Choose upload or approve when saving a starting frame.")
        changed(video, invalidate_avatar=False)
    return scene


def animate_starting_frame(scene, asset_id):
    validate_starting_frame_state(scene, asset_id)
    if starting_frame_status(scene) != "approved":
        raise ValidationError("Approve the current starting frame before animating it.")
    video = scene.video
    context = scene.starting_frame_context
    provider = (video.settings or {}).get("provider")
    target = scene.scene_images.first() or SceneImage(scene=scene)
    target.prompt = context["description"]
    return generate_scene_visual(
        target,
        video,
        context.get("style", "natural"),
        mode=video.mode,
        provider=provider,
        reference=scene.starting_asset.file.path,
    )
