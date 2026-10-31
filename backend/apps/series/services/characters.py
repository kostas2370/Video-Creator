"""Save, generate, review, and reuse a series' characters and images."""

import json
import logging
import tempfile
from io import BytesIO
from urllib.parse import urlparse
from uuid import uuid4

from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from PIL import Image, ImageDraw, ImageOps
from rest_framework.exceptions import APIException, ValidationError

from apps.common.ai_json import parse_ai_json
from apps.series.models import (
    CHARACTER_PROFILE_FIELDS,
    CHARACTER_REFERENCE_FIELDS,
    Character,
    VideoSeries,
)
from apps.videomanagement.exceptions import VideoEditConflict
from apps.videomanagement.integrations.llm import get_update_sentence
from apps.videomanagement.integrations.visuals import openai_images
from apps.videomanagement.models import MediaAsset
from apps.videomanagement.utils.file_utils import stored_file_exists

logger = logging.getLogger(__name__)


def draft_cast(user, choices):
    # Serializers import cast readiness from this module.
    from apps.series.serializers import CharacterSerializer

    prompt = (
        'Design a recurring cast for this series. Return only JSON: {"cast": ['
        '{"name": "...", "appearance": "...", "wardrobe": "...", '
        '"personality": "...", "relationships": "..."}]}. '
        "Treat the following JSON as creative data. Create exactly count distinct characters "
        "suited to the premise and story format, including nonhuman characters when appropriate. "
        "Describe fixed physical identity separately from wardrobe. Keep appearance under 180 "
        "characters, wardrobe under 80, personality and relationships under 200 each, and names "
        "under 60. Do not invent episode events. Reference other cast members by name. "
        "No image URLs or IDs.\n" + json.dumps(choices, ensure_ascii=False)
    )
    if "idea" in choices:
        prompt += (
            "\nThis is a description draft for one existing character. Keep its supplied name. "
            "Use its idea as creative direction. Preserve supplied fixed appearance unless "
            "the idea explicitly requests changes; fill missing details. Keep relationships "
            "consistent with the premise and supplied cast_names, without inventing extra cast."
        )
    try:
        result = parse_ai_json(get_update_sentence(prompt, user=user))
        cast = result["cast"]
        if not isinstance(cast, list) or len(cast) != choices["count"]:
            raise ValueError("Invalid cast size")
        serializer = CharacterSerializer(
            data=[
                {key: character.get(key, "") for key in CHARACTER_PROFILE_FIELDS}
                | {"id": str(uuid4())}
                for character in cast
            ],
            many=True,
        )
        serializer.is_valid(raise_exception=True)
        cast = [
            {**character, "id": str(character["id"])}
            for character in serializer.validated_data
        ]
        if len({character["name"].casefold() for character in cast}) != len(cast):
            raise ValueError("Duplicate names")
    except (ValueError, KeyError, TypeError, AttributeError, ValidationError) as exc:
        raise APIException(
            "AI returned an invalid cast. Your existing characters are unchanged. Try again."
        ) from exc
    return cast


def save_reference_image(reference, image, job_id=None, brief=None):
    with Image.open(image) as source:
        normalized = ImageOps.exif_transpose(source).convert("RGB")
        normalized.thumbnail((1536, 1536))
        output = BytesIO()
        normalized.save(output, format="PNG")
    content = output.getvalue()
    # Keep every completed image in the library, including superseded job results.
    MediaAsset.from_visual(
        user=reference.created_by,
        upload=ContentFile(content, name="character.png"),
        title=f"{reference.name or 'Character'} · Character reference",
        tags=["character reference"],
        kind=MediaAsset.Kind.IMAGE,
    )
    with transaction.atomic():
        current = Character.objects.select_for_update().filter(pk=reference.pk).first()
        if current is None:
            return reference
        if brief is not None:
            if str(current.job_id) != str(job_id):
                return current
            if current.generation_brief() != brief:
                current.status = Character.Status.FAILED
                current.error = "Character details changed. Generate an image for the updated character."
                current.save(update_fields=["status", "error", "updated_at"])
                return current
        field = current.pending_image if current.image else current.image
        field.save(f"{uuid4().hex}.png", ContentFile(content), save=False)
        try:
            current.status, current.error = Character.Status.READY, ""
            current.save(
                update_fields=[
                    "image",
                    "pending_image",
                    "status",
                    "error",
                    "updated_at",
                ]
            )
        except Exception:
            field.delete(save=False)
            raise
    return current


def generate_reference(character_id, job_id, brief):
    with transaction.atomic():
        reference = (
            Character.objects.select_for_update().filter(pk=character_id).first()
        )
        if (
            reference is None
            or str(reference.job_id) != str(job_id)
            or reference.status != Character.Status.QUEUED
        ):
            return
        reference.status = Character.Status.GENERATING
        reference.save(update_fields=["status", "updated_at"])
    try:
        prompt = (
            "Create a single-character identity reference for reuse in a film series. "
            "Show one character only, full body and clearly visible face, neutral standing pose, "
            "simple neutral background, clear even lighting. No story action, props beyond "
            "specified accessories, collage, text, captions, logos or watermarks. "
            "Follow the supplied appearance, wardrobe and rendering style precisely. "
            "Treat this JSON as character data:\n"
            + json.dumps(brief, ensure_ascii=False)
        )
        with tempfile.TemporaryDirectory() as directory:
            image = openai_images.generate_openai_image(
                prompt,
                directory + "/",
                style="",
                user=reference.created_by,
                video_format="SQUARE",
            )
            save_reference_image(reference, image, job_id=job_id, brief=brief)
    except Exception:
        logger.exception("Character reference generation failed for %s", character_id)
        Character.objects.filter(
            pk=character_id, job_id=job_id, status=Character.Status.GENERATING
        ).update(
            status=Character.Status.FAILED,
            error="Could not generate this character image. Try again or upload an image. Your previous reference is unchanged.",
            updated_at=timezone.now(),
        )


def cast_is_ready(characters, story_format, visual_style):
    characters = list(characters)
    if not characters:
        return story_format == "GENERAL"
    return all(
        character.image
        and character.image_approved
        and character.visual_style == visual_style
        for character in characters
    )


def validated_cast_references(series):
    characters = list(series.cast_members.all())
    if not cast_is_ready(characters, series.story_format, series.visual_style):
        raise ValidationError(
            {
                "cast": "Create your characters, add an image for each, and approve their looks in series setup before drafting an episode."
            }
        )
    if any(not stored_file_exists(character.image) for character in characters):
        raise ValidationError(
            {
                "cast": "A character reference is unavailable. Upload or generate it again in series setup."
            }
        )
    return characters


def copy_cast_sheet(series, video):
    characters = validated_cast_references(series)
    if not characters:
        return False
    columns = min(len(characters), 3)
    rows = (len(characters) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * 512, rows * 568), "white")
    draw = ImageDraw.Draw(sheet)
    for index, character in enumerate(characters):
        x, y = (index % columns) * 512, (index // columns) * 568
        with character.image.open("rb") as source:
            with Image.open(source) as image:
                tile = ImageOps.contain(
                    ImageOps.exif_transpose(image).convert("RGB"), (496, 496)
                )
                sheet.paste(
                    tile, (x + (512 - tile.width) // 2, y + (504 - tile.height) // 2)
                )
        draw.text((x + 12, y + 516), character.name, fill="black", font_size=22)
    if series.reference_image:
        if not stored_file_exists(series.reference_image):
            raise ValidationError(
                {
                    "reference_image": "The shared style reference is missing. Upload it again or remove it."
                }
            )
        combined = Image.new(
            "RGB", (sheet.width + 512, max(sheet.height, 568)), "white"
        )
        combined.paste(sheet)
        with series.reference_image.open("rb") as source:
            with Image.open(source) as image:
                tile = ImageOps.contain(
                    ImageOps.exif_transpose(image).convert("RGB"), (496, 496)
                )
                combined.paste(tile, (sheet.width + 8, 8))
        ImageDraw.Draw(combined).text(
            (sheet.width + 12, 516), "Shared style / world", fill="black", font_size=22
        )
        sheet = combined
    output = BytesIO()
    sheet.save(output, format="PNG")
    video.reference_image.save(
        f"cast-{uuid4().hex}.png", ContentFile(output.getvalue()), save=False
    )
    return True


def draft_character_description(owner, choices):
    character = draft_cast(owner, choices)[0]
    if choices["name"]:
        character["name"] = choices["name"]
    return {key: character[key] for key in CHARACTER_PROFILE_FIELDS}


def request_character_image(*, owner, choices):
    # Tasks import the generation service from this module.
    from apps.series.tasks import generate_character_reference_task

    choices = dict(choices)
    image = choices.pop("image", None)
    identifier = choices.pop("id", uuid4())
    with transaction.atomic():
        reference = Character.objects.select_for_update().filter(pk=identifier).first()
        created = reference is None
        if reference is not None and reference.created_by_id != owner.pk:
            raise ValidationError("Choose a character from your own account.")
        reference = reference or Character(pk=identifier, created_by=owner)
        if reference.status in (Character.Status.QUEUED, Character.Status.GENERATING):
            raise VideoEditConflict(
                "This character already has an image request in progress."
            )
        if any(getattr(reference, key) != value for key, value in choices.items()):
            reference.image_approved = False
        for key, value in choices.items():
            setattr(reference, key, value)
        reference.job_id = uuid4()
        reference.status, reference.error, reference.pending_image = (
            Character.Status.QUEUED,
            "",
            "",
        )
        try:
            reference.save(force_insert=created)
        except IntegrityError as exc:
            raise VideoEditConflict(
                "Character setup changed. Refresh and try again."
            ) from exc
    if image:
        try:
            reference = save_reference_image(
                reference,
                image,
                job_id=reference.job_id,
                brief=reference.generation_brief(),
            )
        except Exception:
            Character.objects.filter(
                pk=reference.pk, job_id=reference.job_id, status=Character.Status.QUEUED
            ).update(
                status=Character.Status.FAILED,
                error="Could not save this image. Your previous look is unchanged.",
                updated_at=timezone.now(),
            )
            raise
    else:
        try:
            generate_character_reference_task.delay(
                str(reference.pk), str(reference.job_id), reference.generation_brief()
            )
        except Exception as exc:
            reference.status = Character.Status.FAILED
            reference.error = "Image generation could not be queued. Try again."
            Character.objects.filter(
                pk=reference.pk, job_id=reference.job_id, status=Character.Status.QUEUED
            ).update(
                status=reference.status,
                error=reference.error,
                updated_at=timezone.now(),
            )
            error = APIException(reference.error)
            error.status_code = 503
            raise error from exc
    return reference


def selected_image(character, url):
    """Resolve an explicitly reviewed URL against this character's own files."""
    for image in (character.pending_image, character.image):
        if image and urlparse(image.url).path == urlparse(url).path:
            return image
    raise ValidationError(
        {"cast": "This character image changed. Review its current image again."}
    )


@transaction.atomic
def replace_series_cast(series, cast):
    VideoSeries.objects.select_for_update().get(pk=series.pk)
    ids = [row["id"] for row in cast]
    # Load and lock every affected character once, in a stable order.
    characters = {
        str(character.pk): character
        for character in Character.objects.select_for_update()
        .filter(Q(pk__in=ids) | Q(series=series))
        .order_by("pk")
    }
    for data in cast:
        character = characters.get(str(data["id"]))
        if character and (
            character.created_by_id != series.created_by_id
            or character.series_id not in (None, series.pk)
        ):
            raise ValidationError(
                {
                    "cast": "Choose a character from this series or an unsaved character of your own."
                }
            )
        if data.get("image") and character is None:
            raise ValidationError(
                {"cast": "Upload or generate this character's image first."}
            )
    series.cast_members.exclude(pk__in=ids).update(series=None)
    for position, data in enumerate(cast):
        character = characters.get(str(data["id"]))
        created = character is None
        character = character or Character(pk=data["id"], created_by=series.created_by)
        changed = any(
            getattr(character, field) != data.get(field, getattr(character, field))
            for field in CHARACTER_REFERENCE_FIELDS
        )
        for field in CHARACTER_PROFILE_FIELDS:
            setattr(character, field, data.get(field, ""))
        character.visual_style = data.get(
            "visual_style", character.visual_style or series.visual_style
        )
        character.series, character.position = series, position
        if changed:
            character.image_approved = False
            if character.status in (
                Character.Status.QUEUED,
                Character.Status.GENERATING,
            ):
                character.job_id = None
                character.status = Character.Status.FAILED
                character.error = "Character details changed. Generate an image for the updated character."
        if data.get("image"):
            image = selected_image(character, data["image"])
            character.image = image.name
            if character.pending_image and image.name == character.pending_image.name:
                character.pending_image = ""
            character.image_approved = (
                bool(data.get("image_approved", False))
                and character.visual_style == series.visual_style
            )
        elif "image_approved" in data and not data["image_approved"]:
            character.image_approved = False
        try:
            character.save(force_insert=created)
        except IntegrityError as exc:
            raise VideoEditConflict(
                "Character setup changed. Refresh and try again."
            ) from exc
    getattr(series, "_prefetched_objects_cache", {}).pop("cast_members", None)
