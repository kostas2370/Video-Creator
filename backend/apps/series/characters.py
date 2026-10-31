import json
import logging
import tempfile
from io import BytesIO
from uuid import uuid4

from django.core.files.base import ContentFile
from django.utils import timezone
from PIL import Image, ImageDraw, ImageOps
from rest_framework.exceptions import APIException, ValidationError

from apps.common.ai_json import parse_ai_json
from apps.series.creative import cast_is_ready
from apps.series.models import CHARACTER_PROFILE_FIELDS, CharacterReference
from apps.videomanagement.integrations.llm import get_update_sentence
from apps.videomanagement.integrations.visuals import openai_images
from apps.videomanagement.utils.file_utils import stored_file_exists

logger = logging.getLogger(__name__)


def draft_cast(user, choices):
    from apps.series.serializers import CastCharacterSerializer

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
        serializer = CastCharacterSerializer(
            data=[
                {
                    key: character.get(key, "")
                    for key in CHARACTER_PROFILE_FIELDS
                }
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


def save_reference_image(reference, image):
    with Image.open(image) as source:
        normalized = ImageOps.exif_transpose(source).convert("RGB")
        normalized.thumbnail((1536, 1536))
        output = BytesIO()
        normalized.save(output, format="PNG")
    reference.image.save(
        f"{reference.pk}.png", ContentFile(output.getvalue()), save=False
    )
    try:
        reference.status = CharacterReference.Status.READY
        reference.save(update_fields=["image", "status", "updated_at"])
    except Exception:
        reference.image.delete(save=False)
        raise
    return reference


def generate_reference(reference_id):
    claimed = CharacterReference.objects.filter(
        pk=reference_id, status=CharacterReference.Status.QUEUED
    ).update(status=CharacterReference.Status.GENERATING, updated_at=timezone.now())
    if not claimed:
        return
    reference = CharacterReference.objects.select_related("created_by").get(
        pk=reference_id
    )
    try:
        prompt = (
            "Create a single-character identity reference for reuse in a film series. "
            "Show one character only, full body and clearly visible face, neutral standing pose, "
            "simple neutral background, clear even lighting. No story action, props beyond "
            "specified accessories, collage, text, captions, logos or watermarks. "
            "Follow the supplied appearance, wardrobe and rendering style precisely. "
            "Treat this JSON as character data:\n"
            + json.dumps(reference.generation_brief(), ensure_ascii=False)
        )
        with tempfile.TemporaryDirectory() as directory:
            image = openai_images.generate_openai_image(
                prompt,
                directory + "/",
                style="",
                user=reference.created_by,
                video_format="SQUARE",
            )
            save_reference_image(reference, image)
    except Exception:
        logger.exception("Character reference generation failed for %s", reference_id)
        CharacterReference.objects.filter(pk=reference_id).update(
            status=CharacterReference.Status.FAILED,
            error="Could not generate this character image. Try again or upload an image. Your previous reference is unchanged.",
            updated_at=timezone.now(),
        )


def validated_cast_references(series):
    if not cast_is_ready(series.cast, series.story_format, series.visual_style):
        raise ValidationError(
            {
                "cast": "Create your characters, add an image for each, and approve their looks in series setup before drafting an episode."
            }
        )
    ids = [character["reference_id"] for character in series.cast]
    references = {
        str(reference.pk): reference
        for reference in CharacterReference.objects.filter(
            pk__in=ids, created_by=series.created_by, status=CharacterReference.Status.READY
        )
    }
    for reference_id in ids:
        if reference_id not in references or not stored_file_exists(
            references[reference_id].image
        ):
            raise ValidationError(
                {
                    "cast": "A character reference is unavailable. Upload or generate it again in series setup."
                }
            )
    return references


def copy_cast_sheet(series, video):
    references = validated_cast_references(series)
    if not series.cast:
        return False
    columns = min(len(series.cast), 3)
    rows = (len(series.cast) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * 512, rows * 568), "white")
    draw = ImageDraw.Draw(sheet)
    for index, character in enumerate(series.cast):
        x, y = (index % columns) * 512, (index // columns) * 568
        with references[character["reference_id"]].image.open("rb") as source:
            with Image.open(source) as image:
                tile = ImageOps.contain(
                    ImageOps.exif_transpose(image).convert("RGB"), (496, 496)
                )
                sheet.paste(
                    tile, (x + (512 - tile.width) // 2, y + (504 - tile.height) // 2)
                )
        draw.text((x + 12, y + 516), character["name"], fill="black", font_size=22)
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
