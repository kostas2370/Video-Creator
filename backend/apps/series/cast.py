"""Save a series' characters and their explicitly reviewed images."""
from urllib.parse import urlparse

from django.db import transaction
from rest_framework.exceptions import ValidationError

from .creative import reference_approval
from .models import CHARACTER_PROFILE_FIELDS, Character, VideoSeries


def selected_image(character, url=None):
    if url:
        for image in (character.pending_image, character.image):
            if image and urlparse(image.url).path == urlparse(url).path:
                return image
        raise ValidationError({"cast": "This character image changed. Review its current image again."})
    return character.image or character.pending_image


def validate_cast_images(cast, owner, series=None):
    ids = {row[key] for row in cast for key in ("id", "reference_id", "reference_job_id") if row.get(key)}
    characters = {str(row.pk): row for row in Character.objects.filter(pk__in=ids)}
    for row in cast:
        current = characters.get(str(row["id"]))
        if current and (current.created_by_id != owner.pk or current.series_id not in (None, getattr(series, "pk", None))):
            raise ValidationError({"cast": "Choose a character from this series or an unsaved character of your own."})
        for field in ("reference_id", "reference_job_id"):
            identifier = row.get(field)
            if not identifier:
                continue
            source = characters.get(str(identifier))
            if source is None or source.created_by_id != owner.pk:
                raise ValidationError({"cast": "Choose a character image request from your own account."})
            row[field] = str(identifier)
            if field == "reference_id":
                image = selected_image(source, row.get("reference_image"))
                if not image:
                    raise ValidationError({"cast": "Choose a completed character image."})
                row["reference_image"] = image.url
    return cast


@transaction.atomic
def replace_series_cast(series, cast):
    VideoSeries.objects.select_for_update().get(pk=series.pk)
    validate_cast_images(cast, series.created_by, series)
    series.cast_members.exclude(pk__in=[row["id"] for row in cast]).update(series=None)
    for position, data in enumerate(cast):
        character = Character.objects.filter(pk=data["id"]).first()
        character = character or Character(pk=data["id"], created_by=series.created_by)
        for field in CHARACTER_PROFILE_FIELDS:
            setattr(character, field, data.get(field, ""))
        character.series, character.position = series, position
        character.visual_style = series.visual_style
        source_id = data.get("reference_id")
        if source_id:
            source = Character.objects.get(pk=source_id, created_by=series.created_by)
            image = selected_image(source, data.get("reference_image"))
            character.image = image.name
            if source.pk == character.pk and source.pending_image and image.name == source.pending_image.name:
                character.pending_image = ""
            character.image_approved = data.get("reference_approval") == reference_approval(data, series.visual_style)
            if source.pk != character.pk:
                character.status = Character.Status.READY
        else:
            character.image_approved = False
        job = data.get("reference_job_id")
        if job and str(job) != str(character.pk):
            source = Character.objects.get(pk=job, created_by=series.created_by)
            if source.status in (Character.Status.QUEUED, Character.Status.GENERATING):
                raise ValidationError({"cast": "Wait for this earlier image request to finish before saving."})
            character.pending_image = (source.pending_image or source.image).name
            character.status = source.status
        character.save()
    getattr(series, "_prefetched_objects_cache", {}).pop("cast_members", None)
