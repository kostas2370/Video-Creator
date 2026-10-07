from rest_framework.exceptions import APIException, ValidationError
import logging
import json

from ..models import Scene, Video, SceneImage
from ..request_serializers import AddSceneSerializer, SceneDraftResultSerializer
from ..utils.audio_utils import update_scene as update
from ..utils.llm import get_update_sentence
from ..prompts import format_scene_draft, format_update_form
from ..utils.scenes import create_image_scene, scene_reference
from ..utils.audio_utils import make_scene_speech

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
    update(scene)
    return scene.text


def create_scene(video: Video, data: dict, files: dict) -> Scene:
    data = data.copy()
    serializer = AddSceneSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    try:
        scene = make_scene_speech(
            video,
            serializer.validated_data["text"],
            serializer.validated_data["is_last"],
        )

    except Exception as exc:
        logger.error(exc)
        raise APIException(str(exc), code=400)

    if files.get("image"):
        SceneImage.objects.create(
            scene=scene,
            file=files["image"],
            prompt=serializer.validated_data.get("image_description", ""),
            with_audio=serializer.validated_data["with_audio"],
        )

    elif serializer.validated_data.get("image_description"):
        settings = video.settings or {}
        provider = settings.get("provider")
        create_image_scene(
            video=video,
            image=serializer.validated_data["image_description"],
            text=scene.text,
            dir_name=video.dir_name,
            mode=video.mode,
            provider=provider,
            style=settings.get("style", "natural"),
            reference=scene_reference(scene, video, provider),
            title=video.title,
            user=video.created_by,
            with_audio=serializer.validated_data["with_audio"],
        )

    return scene


def draft_scene(
    video: Video, prompt: str, use_context: bool = False,
    draft_type: str = "sentence", sentence_count: int = 1,
) -> dict:
    """Draft short sentences for review before creating their scenes."""
    scenario = None
    if use_context:
        scenario = {
            "title": video.title,
            "scenes": [
                {"text": scene.text, "is_last": scene.is_last,
                 "visuals": [image.prompt for image in scene.scene_images.all()]}
                for scene in video.scenes.order_by("id").prefetch_related("scene_images")
            ],
        }
    instructions = format_scene_draft(prompt, draft_type, sentence_count, scenario)
    reply = get_update_sentence(instructions, user=video.created_by)
    try:
        # Accept the Markdown fences commonly returned by text-mode providers.
        cleaned = reply.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        result = json.loads(cleaned)
        if not isinstance(result, dict):
            raise ValueError("Invalid draft fields")
        drafts = [result] if sentence_count == 1 else result.get("scenes")
        if not isinstance(drafts, list) or len(drafts) != sentence_count:
            raise ValueError("Incorrect sentence count")
        if any(
            not isinstance(item, dict) or any(
                not isinstance(item.get(field), str) for field in ("text", "image_description")
            ) for item in drafts
        ):
            raise ValueError("Invalid draft fields")
        serializer = SceneDraftResultSerializer(data=drafts, many=True)
        serializer.is_valid(raise_exception=True)
    except (ValueError, IndexError, ValidationError) as exc:
        raise APIException("AI returned an invalid scene draft. Please try again.") from exc
    drafts = [dict(item) for item in serializer.validated_data]
    return drafts[0] if sentence_count == 1 else {"scenes": drafts}
