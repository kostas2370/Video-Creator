"""Persist the ordered cast without changing the API's cast-list shape."""
from django.db import models, transaction

from .models import CHARACTER_PROFILE_FIELDS, SeriesCharacter, VideoSeries


@transaction.atomic
def replace_series_cast(series, cast):
    VideoSeries.objects.select_for_update().get(pk=series.pk)
    rows = SeriesCharacter.objects.filter(series=series)
    rows.exclude(character_id__in=[character["id"] for character in cast]).delete()
    # Move current positions out of the target range before a reorder.
    offset = (rows.aggregate(last=models.Max("position"))["last"] or 0) + len(cast) + 1
    rows.update(position=models.F("position") + offset)
    for position, character in enumerate(cast):
        values = {field: character.get(field, "") for field in CHARACTER_PROFILE_FIELDS}
        values.update(
            position=position,
            reference_id=character.get("reference_id"),
            reference_job_id=character.get("reference_job_id"),
            reference_approval=character.get("reference_approval"),
        )
        SeriesCharacter.objects.update_or_create(
            series=series, character_id=character["id"], defaults=values
        )
    getattr(series, "_prefetched_objects_cache", {}).pop("character_profiles", None)
