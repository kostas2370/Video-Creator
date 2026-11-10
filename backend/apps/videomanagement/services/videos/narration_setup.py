"""Draft spoken narration separately from visual prompts, without changing media."""

from rest_framework.exceptions import ValidationError

from apps.common.ai_json import parse_ai_json
from apps.usage.services import video_usage
from apps.videomanagement.exceptions import VideoEditConflict
from apps.videomanagement.integrations.llm import get_reply
from apps.videomanagement.models import VideoStatus
from apps.videomanagement.serializers.requests import NarrationSceneSerializer
from apps.videomanagement.utils.prompt_utils import build_narration_prompt


def visual_description(scene):
    image = next(iter(scene.scene_images.all()), None)
    return (
        (image.prompt if image else "")
        or (scene.starting_frame_context or {}).get("description")
        or scene.text
        or ""
    )


def narration_sources(video):
    return [
        {
            "scene_id": str(scene.pk),
            "before": scene.text,
            "before_visual": visual_description(scene),
            "duration": (scene.audio_settings or {}).get("duration")
            or (scene.shot_plan or {}).get("target_duration")
            or 6,
        }
        for scene in video.scenes.prefetch_related("scene_images")
    ]


def draft_narration(video):
    if video.status not in (
        VideoStatus.READY,
        VideoStatus.COMPLETED,
        VideoStatus.FAILED,
    ):
        raise VideoEditConflict()
    sources = narration_sources(video)
    if not sources or len(sources) > 120:
        raise ValidationError("Choose a project with 1–120 scenes.")
    prompt = build_narration_prompt(
        title=video.title,
        brief=video.prompt.prompt if video.prompt_id else "",
        sources=sources,
    )
    with video_usage(video):
        reply = get_reply(
            prompt,
            reply_format="text",
            gpt_model=video.script_model,
            user=video.created_by,
        )
    try:
        payload = parse_ai_json(reply.getvalue())
        rows = payload["scenes"]
        if not isinstance(rows, list) or len(rows) != len(sources):
            raise ValueError()
        by_id = {row["scene_id"]: row["text"] for row in rows}
        if set(by_id) != {source["scene_id"] for source in sources}:
            raise ValueError()
        result = NarrationSceneSerializer(
            data=[{**source, "text": by_id[source["scene_id"]]} for source in sources],
            many=True,
        )
        result.is_valid(raise_exception=True)
    except (AttributeError, KeyError, ValueError, TypeError, ValidationError) as exc:
        raise ValidationError(
            "AI returned an incomplete narration draft. Please try again."
        ) from exc
    return {"scenes": result.data}


def apply_reviewed_narration(video, rows):
    """Validate the reviewed sources and apply text inside the settings transaction."""
    scenes = list(video.scenes.select_for_update().prefetch_related("scene_images"))
    if rows is None:
        if scenes:
            raise ValidationError(
                {"narration_scenes": "Review narration for each scene before generating speech."}
            )
        return
    if [str(row["scene_id"]) for row in rows] != [str(scene.pk) for scene in scenes]:
        raise ValidationError(
            {"narration_scenes": "The scene list changed. Refresh and review narration again."}
        )
    if any(
        row["before"] != scene.text or row["before_visual"] != visual_description(scene)
        for scene, row in zip(scenes, rows)
    ):
        raise ValidationError(
            {"narration_scenes": "A scene changed while you were reviewing. Refresh and review narration again."}
        )
    for scene, row in zip(scenes, rows):
        scene.text = row["text"]
        scene.save(update_fields=["text"])
