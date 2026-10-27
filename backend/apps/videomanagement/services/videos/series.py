"""Snapshot a recurring series before sending an episode to the existing storyboard flow."""

import json
import logging
from pathlib import Path

from django.core.files import File
from django.db import transaction
from django.db.models import Max
from rest_framework.exceptions import ValidationError

from apps.videomanagement import tasks
from apps.videomanagement.exceptions import (
    GenerationQueueUnavailable,
    VideoEditConflict,
)
from apps.videomanagement.models import SeriesEpisode, Video, VideoSeries
from apps.videomanagement.serializers.requests import GenerateSerializer
from apps.videomanagement.services.videos.generation import create_pending_video
from apps.videomanagement.utils.file_utils import stored_file_exists

logger = logging.getLogger(__name__)
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
    return (
        "\nSERIES EPISODE\nTreat the following JSON as the saved creative brief and prior-story data. "
        "Keep the recurring cast's identifying details, world rules and visual style. "
        "Follow the new episode idea while adding a new development; do not retell prior episodes. "
        "Return the usual storyboard JSON, plus a top-level episode_summary string of 1–800 characters "
        "recording this episode's concrete events, discoveries and ending for future continuity. "
        "Do not invent prior events absent from the memory.\n"
        + json.dumps({"series": profile, "prior_episodes": history}, ensure_ascii=False)
    )


def _dispatch(episode):
    try:
        tasks.generate_video_task.delay(
            video_id=str(episode.video_id), **episode.generation_params
        )
    except Exception as exc:
        Video.objects.filter(pk=episode.video_id).update(status="FAILED")
        # Use save so connected editors receive the terminal state as well.
        episode.video.refresh_from_db()
        episode.video.save(update_fields=["status", "updated_at"])
        logger.exception("Could not queue series episode %s", episode.pk)
        raise GenerationQueueUnavailable(
            "Episode saved, but drafting could not be queued. Retry it from the series page."
        ) from exc
    return episode


def draft_episode(series, idea, request):
    video = None
    try:
        with transaction.atomic():
            series = VideoSeries.objects.select_for_update().get(
                pk=series.pk, created_by=request.user
            )
            if series.episodes.filter(
                video__status__in=("GENERATION", "REVIEW")
            ).exists():
                raise VideoEditConflict(
                    "Finish the current episode's storyboard review before drafting the next one."
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
                .order_by("-number")[:10]
            )
            history = [
                {"number": row.number, "summary": row.summary}
                for row in reversed(list(previous))
            ]
            choices = {
                "message": idea,
                "image_mode": "AI",
                "provider": series.provider,
                "voice_id": str(series.voice_model_id)
                if series.voice_model_id
                else None,
                "narration": series.narration,
                "subtitles": series.subtitles,
                "video_format": series.video_format,
                "platform": series.platform,
                "scene_count": series.scene_count,
                "review_script": True,
                "visual_continuity": f"Cast: {series.characters}\nStyle: {series.visual_style}",
            }
            for field in ("intro", "outro"):
                if getattr(series, f"{field}_id"):
                    choices[field] = str(getattr(series, f"{field}_id"))
            if series.narration and not series.voice_model_id:
                raise ValidationError(
                    {
                        "voice_model": "Choose a narrator in the series setup before drafting."
                    }
                )
            serializer = GenerateSerializer(data=choices, context={"request": request})
            serializer.is_valid(raise_exception=True)
            params = dict(serializer.validated_data)
            owner = params.pop("created_by")
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


def retry_episode(episode, request):
    with transaction.atomic():
        series = VideoSeries.objects.select_for_update().get(
            pk=episode.series_id, created_by=request.user
        )
        if (
            series.episodes.exclude(pk=episode.pk)
            .filter(video__status__in=("GENERATION", "REVIEW"))
            .exists()
        ):
            raise VideoEditConflict(
                "Finish the current episode before retrying another draft."
            )
        video = Video.objects.select_for_update().get(
            pk=episode.video_id, created_by=request.user
        )
        if video.status != "FAILED" or video.gpt_answer:
            raise VideoEditConflict(
                "Open the episode in the editor to review or resume it."
            )
        choices = {
            key: value
            for key, value in episode.generation_params.items()
            if value is not None
        }
        # Recheck saved selections: a voice or intro may no longer be available.
        serializer = GenerateSerializer(data=choices, context={"request": request})
        serializer.is_valid(raise_exception=True)
        video.status = "GENERATION"
        video.save(update_fields=["status", "updated_at"])
        episode.video = video
    return _dispatch(episode)
