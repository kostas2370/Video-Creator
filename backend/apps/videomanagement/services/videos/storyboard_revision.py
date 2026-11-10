from rest_framework.exceptions import ValidationError

from apps.common.ai_json import parse_ai_json
from apps.usage.services import video_usage
from apps.videomanagement.integrations.llm import get_reply, script_errors
from apps.videomanagement.integrations.visuals.registry import ImageProviderRegistry
from apps.videomanagement.models import VideoStatus
from apps.videomanagement.serializers.requests import StoryboardSerializer
from apps.videomanagement.utils.prompt_utils import build_storyboard_revision_prompt


def revise_storyboard(video, *, storyboard, instructions):
    if video.status != VideoStatus.REVIEW:
        raise ValidationError("This project is no longer awaiting storyboard review.")
    settings = video.settings or {}
    params = settings.get("generation_params") or {}
    narration = settings.get("narration", True)
    video_provider = ImageProviderRegistry.is_video(
        settings.get("provider"), user=video.created_by, mode=video.mode
    )
    prompt = build_storyboard_revision_prompt(
        storyboard,
        instructions,
        field_specification=str(StoryboardSerializer()),
        project_context={
            "prompt": video.prompt.prompt if video.prompt_id else "",
            "series_context": params.get("series_context", ""),
        },
        settings=settings,
        image_mode=video.mode,
        video_provider=video_provider,
    )
    with video_usage(video):
        response = get_reply(
            prompt,
            reply_format="text",
            gpt_model=video.script_model,
            user=video.created_by,
        )
    try:
        data = parse_ai_json(response.getvalue())
        # Models sometimes express an unused optional diagram as {} instead of null.
        if isinstance(data, dict) and isinstance(data.get("scenes"), list):
            for scene in data["scenes"]:
                if not isinstance(scene, dict) or not isinstance(
                    scene.get("sentences"), list
                ):
                    continue
                for shot in scene["sentences"]:
                    editing = shot.get("editing") if isinstance(shot, dict) else None
                    if isinstance(editing, dict) and editing.get("diagram") == {}:
                        editing["diagram"] = None
        result = StoryboardSerializer(
            data=data,
            context={
                "narration": narration,
                "user": video.created_by,
                "video_provider": video_provider,
            },
        )
        result.is_valid(raise_exception=True)
        revised = dict(result.validated_data)
        # These are render choices, not AI editing instructions.
        revised["generation_mode"] = storyboard.get(
            "generation_mode", settings.get("generation_mode", "STANDARD")
        )
        errors = script_errors(
            revised,
            narration=narration,
            user=video.created_by,
            ai_scene_editing=settings.get("ai_scene_editing", False),
            video_provider=video_provider,
        )
        if errors:
            raise ValidationError(errors)
    except (ValueError, TypeError, AttributeError, ValidationError) as exc:
        raise ValidationError(
            "AI returned an invalid storyboard. Please try again."
        ) from exc
    return revised
