"""Cuts on the full edit, after scene cuts, without changing source scenes."""

import math

from apps.videomanagement.exceptions import VideoEditConflict
from apps.videomanagement.services.scenes.editing import changed, editable_video
from apps.videomanagement.services.videos.preview import preview_timeline
from apps.videomanagement.utils.cuts import video_cut_source


def update_video_cuts(video, *, source_duration, source_key, sections, previous):
    with editable_video(video.pk) as locked:
        source = video_cut_source(preview_timeline(locked).segments)
        if (
            locked.cuts != previous
            or source_key != source["key"]
            or not math.isclose(source_duration, source["duration"], abs_tol=0.001)
        ):
            raise VideoEditConflict(
                "This timeline changed. Reopen Cut video before saving."
            )
        locked.cuts = {
            "source_duration": source["duration"],
            "source_key": source_key,
            "sections": sections,
        }
        locked.save(update_fields=["cuts"])
        changed(locked, invalidate_avatar=False)
    return locked
