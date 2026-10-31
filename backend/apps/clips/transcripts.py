import hashlib
import math

from django.db.models import Q
from rest_framework.exceptions import ValidationError

from apps.videomanagement.utils.captions.timing import words_in_range

from .models import ClipProject


def validate_range(start, end, minimum, duration=None):
    if not math.isfinite(start) or (end is not None and not math.isfinite(end)):
        raise ValidationError("Enter finite times for the processing range.")
    stop = duration if end is None else end
    if start < 0 or (stop is not None and stop - start < minimum):
        raise ValidationError(
            "Choose a range at least as long as the minimum clip length."
        )
    if duration is not None and (start >= duration or stop > duration):
        raise ValidationError("Choose a processing range within the source video.")


def source_key(project):
    if project.youtube_url:
        return hashlib.sha256(project.youtube_url.encode()).hexdigest()
    with project.source.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def reuse_transcript(project):
    candidates = (
        ClipProject.objects.filter(
            created_by_id=project.created_by_id,
            range_start__lte=project.range_start,
        )
        .exclude(pk=project.pk)
        .exclude(words=[])
        .filter(
            Q(range_end__gte=project.range_stop)
            | Q(range_end=None, duration__gte=project.range_stop)
        )
        .filter(Q(source_key=project.source_key) | Q(source_key=""))
        .defer("words", "transcript_parts")
    )
    for candidate in candidates:
        key = candidate.source_key
        if not key:
            if project.youtube_url != candidate.youtube_url:
                continue
            if not project.youtube_url:
                if not candidate.source or not candidate.source.storage.exists(
                    candidate.source.name
                ):
                    continue
                if candidate.source.size != project.source.size:
                    continue
            key = source_key(candidate)
            ClipProject.objects.filter(pk=candidate.pk, source_key="").update(
                source_key=key
            )
        if key == project.source_key:
            return words_in_range(
                candidate.words, project.range_start, project.range_stop
            )
    return None
