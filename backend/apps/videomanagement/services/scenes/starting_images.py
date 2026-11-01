from rest_framework.exceptions import ValidationError

from apps.videomanagement.integrations.visuals import ImageProviderRegistry
from apps.videomanagement.models import ImageMode, MediaAsset, SceneImage
from apps.videomanagement.services.scenes.editing import changed, editable_video
from apps.videomanagement.services.scenes.visuals import (
    planned_visual_prompt,
    reference_role_for,
    starting_frame_key,
    visual_generation_duration,
)
from apps.videomanagement.utils.file_utils import stored_file_exists


def requires_starting_image(video):
    return bool(
        (video.settings or {}).get("character_references")
        and video.mode == ImageMode.AI
        and ImageProviderRegistry.is_video(
            (video.settings or {}).get("provider"),
            user=video.created_by,
            mode=video.mode,
        )
    )


def current_key(scene, description, style):
    video = scene.video
    return starting_frame_key(
        video,
        planned_visual_prompt(
            scene, description, video.mode, (video.settings or {}).get("provider")
        ),
        style,
    )


def starting_image_status(scene):
    context = scene.starting_image_context or {}
    if not scene.starting_asset_id or not stored_file_exists(scene.starting_asset.file):
        return "missing"
    if context.get("key") != current_key(
        scene, context.get("description", ""), context.get("style", "natural")
    ):
        return "needs_review"
    return (
        "approved"
        if context.get("approved_asset") == str(scene.starting_asset_id)
        else "needs_review"
    )


def checked_scene(scene, asset_id):
    if not requires_starting_image(scene.video):
        raise ValidationError(
            "Starting-image review is available for character video shots."
        )
    if not ImageProviderRegistry.supports_reference(
        (scene.video.settings or {}).get("provider")
    ):
        raise ValidationError(
            "Choose a video provider with reference-image support for this cast."
        )
    if str(scene.starting_asset_id or "") != str(asset_id or ""):
        raise ValidationError(
            "The starting image changed. Refresh and review it again."
        )
    return scene


def save_starting_image(
    scene, *, operation, asset_id=None, image=None, image_description=None
):
    with editable_video(scene.video_id) as video:
        scene.refresh_from_db()
        scene.video = video
        checked_scene(scene, asset_id)
        context = dict(scene.starting_image_context or {})
        if operation == "upload":
            description = image_description or context.get("description", "")
            if not description:
                raise ValidationError(
                    "Add a shot description before uploading a starting image."
                )
            style = (video.settings or {}).get("style", "natural")
            asset = MediaAsset.from_visual(
                user=video.created_by,
                upload=image,
                title=f"{video.title} · Scene {scene.position} starting image",
                tags=["starting image"],
                kind=MediaAsset.Kind.IMAGE,
                source_video=video,
            )
            scene.starting_asset = asset
            context = {
                "description": description,
                "style": style,
                "key": current_key(scene, description, style),
            }
        elif operation == "approve":
            if starting_image_status(scene) == "missing":
                raise ValidationError("Prepare a starting image before approving it.")
            if context.get("key") != current_key(
                scene, context.get("description", ""), context.get("style", "natural")
            ):
                raise ValidationError(
                    "The shot settings changed. Prepare and review a new starting image."
                )
            context["approved_asset"] = str(scene.starting_asset_id)
        scene.starting_image_context = context
        scene.save(update_fields=["starting_asset", "starting_image_context"])
        changed(video, invalidate_avatar=False)
    return scene


def animate_starting_image(scene, asset_id):
    checked_scene(scene, asset_id)
    if starting_image_status(scene) != "approved":
        raise ValidationError("Approve the current starting image before animating it.")
    video = scene.video
    context = scene.starting_image_context
    provider = (video.settings or {}).get("provider")
    generate = ImageProviderRegistry.resolve(video.mode, provider)
    result = generate(
        planned_visual_prompt(scene, context["description"], video.mode, provider),
        f"{video.dir_name}/images/",
        style=context.get("style", "natural"),
        title=video.title,
        user=video.created_by,
        reference=scene.starting_asset.file.path,
        reference_role=reference_role_for(video, scene.starting_asset.file.path),
        duration=visual_generation_duration(scene),
        video_format=(video.settings or {}).get("video_format", "LANDSCAPE"),
    )
    if not result:
        raise RuntimeError("The visual provider returned no video")
    target = scene.scene_images.first() or SceneImage(scene=scene)
    target.file = result
    target.prompt = context["description"]
    target.save()
    return target
