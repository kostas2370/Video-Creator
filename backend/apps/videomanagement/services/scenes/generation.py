import logging

from apps.usage.services import video_usage

from rest_framework.exceptions import APIException, ValidationError

from apps.common.ai_json import parse_ai_json
from apps.videomanagement.integrations.llm import get_update_sentence
from apps.videomanagement.integrations.visuals.registry import ImageProviderRegistry
from apps.videomanagement.models import Scene, SceneImage, Video
from apps.videomanagement.schemas.drafts import SceneDraftResultSerializer
from apps.videomanagement.services.scenes.narration import make_scene_speech
from apps.videomanagement.services.scenes.narration import update_scene as update
from apps.videomanagement.services.scenes.visuals import (
    create_image_scene,
    scene_reference,
)
from apps.videomanagement.utils.prompt_utils import (
    build_scene_draft_prompt,
    format_update_form,
    with_visual_continuity,
)

logger = logging.getLogger(__name__)


def generate_scene(text: str, scene: Scene) -> str:
    """
    Generate an updated version of the scene text and update the scene with it.

    Args:
        text (str): The new text for the scene.
        scene (Scene): The scene instance to update.

    Returns:
        str: The updated text for the scene.
    """

    if text == scene.text.strip():
        return text

    with video_usage(scene.video):
        text = get_update_sentence(
            format_update_form(scene.text, text), user=scene.video.created_by
        )

    return text


def update_scene(text: str, scene: Scene):
    """
    Update the text of a scene with new content.

    Args:
        text (str): The new text content for the scene.
        scene (Scene): The scene object to update.

    Returns:
        str: The updated text content of the scene.
    """
    new_text = text
    scene.text = new_text if new_text else scene.text
    if (scene.video.settings or {}).get("narration", True):
        update(scene)
    scene.save(update_fields=["text"])
    return scene.text


def create_scene(video: Video, data: dict, files: dict) -> Scene:
    if not data.get("text", "").strip():
        raise ValidationError("Add dialogue for this scene.")
    try:
        scene = make_scene_speech(
            video,
            data["text"],
            data.get("is_last", False),
            position=data.get("position"),
        )

    except ValidationError:
        raise
    except Exception as exc:
        logger.error(exc)
        raise APIException(str(exc), code=400)

    if files.get("image"):
        SceneImage.objects.create(
            scene=scene,
            file=files["image"],
            prompt=data.get("image_description", ""),
            with_audio=data.get("with_audio", False),
        )

    elif data.get("image_description"):
        settings = video.settings or {}
        provider = settings.get("provider")
        create_image_scene(
            video=video,
            scene=scene,
            image=data["image_description"],
            text=scene.text,
            dir_name=video.dir_name,
            mode=video.mode,
            provider=provider,
            style=settings.get("style", "natural"),
            reference=scene_reference(scene, video, provider),
            title=video.title,
            user=video.created_by,
            with_audio=data.get("with_audio", False),
        )

    return scene


def draft_scene(
    video: Video,
    prompt: str,
    use_context: bool = False,
    draft_type: str = "sentence",
    sentence_count: int = 1,
) -> dict:
    """Draft short sentences for review before creating their scenes."""
    scenario = None
    if use_context:
        scenario = {
            "title": video.title,
            "scenes": [
                {
                    "text": scene.text,
                    "is_last": scene.is_last,
                    "visuals": [image.prompt for image in scene.scene_images.all()],
                }
                for scene in video.scenes.order_by("position").with_media()
            ],
        }
    settings = video.settings or {}
    instructions = build_scene_draft_prompt(
        prompt, draft_type, sentence_count, scenario, image_mode=video.mode,
        video=ImageProviderRegistry.is_video(
            settings.get("provider"), user=video.created_by, mode=video.mode
        ),
        style=settings.get("style", ""),
    )
    if video.mode == "AI" or video.video_type == "MANUAL":
        instructions = with_visual_continuity(
            instructions, settings.get("visual_continuity", "")
        )
    reply = get_update_sentence(instructions, user=video.created_by)
    try:
        result = parse_ai_json(reply)
        serializer = SceneDraftResultSerializer(
            data=[result] if sentence_count == 1 else result["scenes"],
            many=True,
            min_length=sentence_count,
            max_length=sentence_count,
        )
        serializer.is_valid(raise_exception=True)
    except (ValueError, KeyError, TypeError, IndexError, ValidationError) as exc:
        raise APIException(
            "AI returned an invalid scene draft. Please try again."
        ) from exc
    drafts = serializer.validated_data
    return drafts[0] if sentence_count == 1 else {"scenes": drafts}
