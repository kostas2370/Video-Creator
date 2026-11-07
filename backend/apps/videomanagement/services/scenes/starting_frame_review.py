import hashlib
import json
from io import BytesIO

from django.conf import settings as django_settings
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageDraw, ImageOps
from rest_framework.exceptions import ValidationError

from apps.common.ai_json import parse_ai_json
from apps.usage.services import video_usage
from apps.videomanagement.integrations.llm import get_reply
from apps.videomanagement.models import Scene, Video
from apps.videomanagement.serializers.starting_frame_review import (
    StartingFrameReviewResultSerializer,
)
from apps.videomanagement.services.scenes.starting_frames import (
    validate_starting_frame_scene,
    current_frame_key,
    starting_frame_current,
)
from apps.videomanagement.utils.file_utils import stored_file_exists
from apps.videomanagement.utils.prompt_utils import build_starting_frame_review_prompt


def review_model(video):
    """Use the saved script model, including parameters retained by older projects."""
    settings = video.settings or {}
    model = settings.get("gpt_model") or (settings.get("generation_params") or {}).get(
        "gpt_model"
    )
    if not model:
        episode = getattr(video, "series_episode", None)
        model = (episode.generation_params or {}).get("gpt_model") if episode else None
    return model or django_settings.DEFAULT_GPT_MODEL


def review_source_key(scene):
    context = scene.starting_frame_context or {}
    video = scene.video
    settings = video.settings or {}
    source = {
        "version": 1,
        "asset": str(scene.starting_asset_id or ""),
        "file": scene.starting_asset.file.name if scene.starting_asset_id else "",
        "description": context.get("description", ""),
        "frame_key": context.get("key"),
        "current_key": current_frame_key(
            scene, context.get("description", ""), context.get("style", "natural")
        ),
        "text": scene.text,
        "shot_plan": scene.shot_plan,
        "continuity": settings.get("visual_continuity", ""),
        "model": review_model(video),
        "archived_at": str(scene.archived_at or ""),
    }
    return hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest()


def current_saved_review(scene):
    review = (scene.starting_frame_context or {}).get("ai_review")
    if (
        isinstance(review, dict)
        and review.get("source_key") == review_source_key(scene)
        and scene.starting_asset_id
        and stored_file_exists(scene.starting_asset.file)
    ):
        return review
    return None


def validate_review_source(scene, source_key=None, *, asset_id=None):
    validate_starting_frame_scene(
        scene, scene.starting_asset_id if asset_id is None else asset_id
    )
    if (
        scene.archived_at
        or not scene.starting_asset_id
        or not stored_file_exists(scene.starting_asset.file)
    ):
        raise ValidationError(
            "Prepare a starting frame before requesting an AI review."
        )
    if not stored_file_exists(scene.video.reference_image):
        raise ValidationError(
            "The character reference is missing. Restore it before reviewing."
        )
    if not starting_frame_current(scene):
        raise ValidationError(
            "The shot settings changed. Prepare a new starting frame before reviewing."
        )
    current_source_key = review_source_key(scene)
    if source_key is not None and current_source_key != source_key:
        raise ValidationError(
            "The frame or shot changed. Review the current frame again."
        )
    return current_source_key


def review_comparison_sheet(scene):
    sheet = Image.new("RGB", (1536, 800), "white")
    draw = ImageDraw.Draw(sheet)
    for index, (label, field) in enumerate(
        [
            ("CHARACTER REFERENCE (identity only)", scene.video.reference_image),
            ("STARTING FRAME TO REVIEW", scene.starting_asset.file),
        ]
    ):
        left = index * 768
        draw.text((left + 16, 12), label, fill="black")
        with field.open("rb") as source, Image.open(source) as original:
            image = ImageOps.exif_transpose(original).convert("RGB")
            image.thumbnail((744, 752))
            sheet.paste(
                image, (left + (768 - image.width) // 2, 40 + (752 - image.height) // 2)
            )
    output = BytesIO()
    sheet.save(output, format="JPEG", quality=90)
    output.seek(0)
    return output


def review_starting_frame(scene, source_key):
    validate_review_source(scene, source_key)
    context = scene.starting_frame_context or {}
    settings = scene.video.settings or {}
    brief = {
        "shot_description": context.get("description", ""),
        "shot_plan": scene.shot_plan,
        "story_context": scene.text,
        "character_and_setting_guidance": settings.get("visual_continuity", ""),
        "style": context.get("style", "natural"),
    }
    try:
        reference = review_comparison_sheet(scene)
    except OSError as exc:
        raise ValidationError(
            "The review images could not be read. Restore them and retry."
        ) from exc
    with reference, video_usage(scene.video):
        response = get_reply(
            build_starting_frame_review_prompt(brief),
            reply_format="text",
            gpt_model=review_model(scene.video),
            user=scene.video.created_by,
            reference_image=reference,
        )
    try:
        result = StartingFrameReviewResultSerializer(
            data=parse_ai_json(response.getvalue())
        )
        result.is_valid(raise_exception=True)
    except (ValueError, TypeError, KeyError, ValidationError) as exc:
        raise ValidationError(
            "AI returned an invalid starting frame review. Please try again."
        ) from exc
    review = {
        **result.validated_data,
        "source_key": source_key,
        "checked_at": timezone.now().isoformat(),
    }
    with transaction.atomic():
        video = Video.objects.select_for_update().get(
            pk=scene.video_id, created_by=scene.video.created_by
        )
        current = Scene.objects.select_for_update().get(pk=scene.pk, video=video)
        current.video = video
        # Recheck under the lock: a frame may change while the AI is working.
        validate_review_source(current, source_key)
        current.starting_frame_context = {
            **current.starting_frame_context,
            "ai_review": review,
        }
        current.save(update_fields=["starting_frame_context"])
    return review
