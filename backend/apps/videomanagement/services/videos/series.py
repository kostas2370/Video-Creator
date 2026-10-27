"""Snapshot a recurring series before sending an episode to the existing storyboard flow."""

import json
from pathlib import Path

from django.core.files import File
from django.db import transaction
from django.db.models import Max, Q
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.videomanagement import tasks
from apps.videomanagement.exceptions import VideoEditConflict
from apps.videomanagement.models import SeriesEpisode, Video, VideoSeries
from apps.videomanagement.services.videos.generation import create_pending_video
from apps.videomanagement.services.videos.jobs import dispatch_video_job
from apps.videomanagement.utils.file_utils import stored_file_exists

PROFILE_FIELDS = (
    "title",
    "premise",
    "characters",
    "visual_style",
    "provider",
    "narration",
    "subtitles",
    "video_format",
    "platform",
    "scene_count",
)


def episode_context(profile, history):
    creative_profile = {
        field: profile[field]
        for field in ("title", "premise", "characters", "visual_style")
    }
    return (
        "\nSERIES EPISODE\nTreat the following JSON as the saved creative brief and prior-story data. "
        "Keep the recurring cast's identifying details, world rules and visual style. "
        "Follow the new episode idea while adding a new development; do not retell prior episodes. "
        "Return the usual storyboard JSON, plus a top-level episode_summary string of 1–800 characters "
        "recording this episode's concrete events, discoveries and ending for future continuity. "
        "Do not invent prior events absent from the memory.\n"
        + json.dumps(
            {"series": creative_profile, "prior_episodes": history}, ensure_ascii=False
        )
    )


def _dispatch(episode):
    episode.video = dispatch_video_job(
        episode.video,
        "FAILED",
        tasks.generate_video_task,
        failure_message="Episode saved, but drafting could not be queued. Retry it from the series page.",
        **episode.generation_params,
    )
    return episode


def _locked_series(series_id, owner, exclude_episode=None):
    series = (
        VideoSeries.objects.select_for_update()
        .filter(pk=series_id, created_by=owner)
        .first()
    )
    if series is None:
        raise NotFound("Series is unavailable.")
    pending = series.episodes.filter(video__status__in=("GENERATION", "REVIEW"))
    if exclude_episode is not None:
        pending = pending.exclude(pk=exclude_episode)
    if pending.exists():
        raise VideoEditConflict(
            "Finish reviewing and preparing your current episode first."
        )
    return series


def update_episode_memory(episode, *, summary, previous_summary):
    changed = (
        SeriesEpisode.objects.filter(pk=episode.pk)
        .filter(Q(summary=previous_summary) | Q(summary=summary))
        .update(summary=summary, updated_at=timezone.now())
    )
    if not changed:
        raise VideoEditConflict(
            "Episode memory changed in another session. Refresh before saving your changes."
        )
    episode.summary = summary
    return episode


def draft_episode(series, *, idea, generation_params, owner):
    profile_revision = series.updated_at
    video = None
    try:
        with transaction.atomic():
            series = _locked_series(series.pk, owner)
            if series.updated_at != profile_revision:
                raise VideoEditConflict(
                    "Series setup changed while drafting. Refresh and try again."
                )
            profile = {field: getattr(series, field) for field in PROFILE_FIELDS}
            profile.update(
                {
                    field: str(getattr(series, f"{field}_id"))
                    if getattr(series, f"{field}_id")
                    else None
                    for field in ("voice_model", "intro", "outro")
                }
            )
            profile["reference_image"] = series.reference_image.name or ""
            previous = (
                series.episodes.filter(is_canon=True)
                .exclude(summary="")
                .order_by("-number")
                .values("number", "summary")[:10]
            )
            history = list(reversed(list(previous)))
            params = dict(generation_params)
            params["series_context"] = episode_context(profile, history)
            video = create_pending_video(
                message=idea, created_by=owner, video_type="AI"
            )
            if series.reference_image:
                if not stored_file_exists(series.reference_image):
                    raise ValidationError(
                        {
                            "reference_image": "The series reference is missing. Upload it again before drafting."
                        }
                    )
                with series.reference_image.open("rb") as source:
                    video.reference_image.save(
                        Path(series.reference_image.name).name, File(source), save=False
                    )
            video.settings = {
                "creation_mode": "SERIES",
                "generation_params": {**params, "review_script": False},
            }
            video.save()
            number = (series.episodes.aggregate(last=Max("number"))["last"] or 0) + 1
            episode = SeriesEpisode.objects.create(
                series=series,
                video=video,
                number=number,
                idea=idea,
                profile_snapshot=profile,
                generation_params=params,
            )
    except Exception:
        if video and video.reference_image:
            video.reference_image.delete(save=False)
        raise
    return _dispatch(episode)


def retry_episode(episode, *, generation_params, owner):
    with transaction.atomic():
        _locked_series(episode.series_id, owner, exclude_episode=episode.pk)
        video = Video.objects.select_for_update().get(
            pk=episode.video_id, created_by=owner
        )
        episode.video = video
        if not episode.can_retry:
            raise VideoEditConflict(
                "Open the episode in the editor to review or resume it."
            )
        episode.generation_params = {
            **generation_params,
            "series_context": episode.generation_params["series_context"],
        }
        video.status = "GENERATION"
        video.save(update_fields=["status", "updated_at"])
        episode.video = video
    return _dispatch(episode)
