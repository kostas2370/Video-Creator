from django.db import transaction

from apps.videomanagement.events import publish_update
from apps.videomanagement.exceptions import VideoEditConflict
from apps.videomanagement.models import Video


def update_notes(video, *, notes, previous_notes):
    with transaction.atomic():
        video = Video.objects.select_for_update().get(pk=video.pk)
        if video.notes not in (previous_notes, notes):
            raise VideoEditConflict(
                {
                    "detail": "Notes changed in another session. Your draft has been kept.",
                    "notes": video.notes,
                }
            )
        video.notes = notes
        video.save(update_fields=["notes"])
        publish_update(f"video.{video.pk}", video_id=video.pk)
    return video
