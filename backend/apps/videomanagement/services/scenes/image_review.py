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
from apps.videomanagement.serializers.image_review import ImageReviewResultSerializer
from apps.videomanagement.services.scenes.starting_images import (
    checked_scene,
    current_key,
    starting_image_current,
    starting_image_status,
)
from apps.videomanagement.utils.file_utils import stored_file_exists
from apps.videomanagement.utils.prompt_utils import build_image_review_prompt


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


def review_key(scene):
    context = scene.starting_image_context or {}
    video = scene.video
    settings = video.settings or {}
    source = {
        "version": 1,
        "asset": str(scene.starting_asset_id or ""),
        "file": scene.starting_asset.file.name if scene.starting_asset_id else "",
        "description": context.get("description", ""),
        "frame_key": context.get("key"),
        "current_key": current_key(
            scene, context.get("description", ""), context.get("style", "natural")
        ),
        "text": scene.text,
        "shot_plan": scene.shot_plan,
        "continuity": settings.get("visual_continuity", ""),
        "model": review_model(video),
        "archived_at": str(scene.archived_at or ""),
    }
    return hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest()


def saved_review(scene):
    review = (scene.starting_image_context or {}).get("ai_review")
    if (
        isinstance(review, dict)
        and review.get("source_key") == review_key(scene)
        and starting_image_status(scene) != "missing"
    ):
        return review
    return None


def check_review_source(scene, source_key=None):
    checked_scene(scene, scene.starting_asset_id)
    if scene.archived_at or starting_image_status(scene) == "missing":
        raise ValidationError(
            "Prepare a starting image before requesting an AI review."
        )
    if not stored_file_exists(scene.video.reference_image):
        raise ValidationError(
            "The character reference is missing. Restore it before reviewing."
        )
    if not starting_image_current(scene):
        raise ValidationError(
            "The shot settings changed. Prepare a new starting image before reviewing."
        )
    if source_key is not None and review_key(scene) != source_key:
        raise ValidationError(
            "The image or shot changed. Review the current image again."
        )
    return review_key(scene)


def comparison_image(scene):
    sheet = Image.new("RGB", (1536, 800), "white")
    draw = ImageDraw.Draw(sheet)
    for index, (label, field) in enumerate(
        [
            ("CHARACTER REFERENCE (identity only)", scene.video.reference_image),
            ("STARTING IMAGE TO REVIEW", scene.starting_asset.file),
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


def review_starting_image(scene, source_key):
    check_review_source(scene, source_key)
    context = scene.starting_image_context or {}
    settings = scene.video.settings or {}
    brief = {
        "shot_description": context.get("description", ""),
        "shot_plan": scene.shot_plan,
        "story_context": scene.text,
        "character_and_setting_guidance": settings.get("visual_continuity", ""),
        "style": context.get("style", "natural"),
    }
    try:
        with comparison_image(scene) as reference, video_usage(scene.video):
            response = get_reply(
                build_image_review_prompt(brief),
                reply_format="text",
                gpt_model=review_model(scene.video),
                user=scene.video.created_by,
                reference_image=reference,
            )
        result = ImageReviewResultSerializer(data=parse_ai_json(response.getvalue()))
        result.is_valid(raise_exception=True)
    except (ValueError, TypeError, KeyError, ValidationError) as exc:
        raise ValidationError(
            "AI returned an invalid image review. Please try again."
        ) from exc
    except OSError as exc:
        raise ValidationError(
            "The review images could not be read. Restore them and retry."
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
        check_review_source(current, source_key)
        current.starting_image_context = {
            **current.starting_image_context,
            "ai_review": review,
        }
        current.save(update_fields=["starting_image_context"])
    return review
