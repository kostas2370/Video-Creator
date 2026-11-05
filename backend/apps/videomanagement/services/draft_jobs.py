"""Recoverable, owner-bound AI drafts using the existing Celery result backend."""

from uuid import uuid4

from celery.result import AsyncResult
from django.core import signing
from rest_framework.exceptions import APIException, NotFound
from rest_framework.response import Response

SALT = "ai-draft-job-v1"
MAX_AGE = 86400
OPERATIONS = {
    "story",
    "scene",
    "cast",
    "character",
    "memory",
    "tags",
    "save_tags",
    "description",
    "hashtags",
    "clip_search",
    "rewrite",
}


def draft_response(request, operation, values, synchronous):
    # Keep the response contract of older API clients. The app requests jobs explicitly.
    if "respond-async" not in request.headers.get("Prefer", ""):
        return Response(synchronous())
    return Response(
        queue_draft(request.user, operation, values),
        status=202,
        headers={"Preference-Applied": "respond-async", "Cache-Control": "no-store"},
    )


class DraftQueueUnavailable(APIException):
    status_code = 503
    default_detail = "Could not queue the draft. Please try again."


def queue_draft(user, operation, values):
    from apps.videomanagement.tasks import draft_ai_task

    if operation not in OPERATIONS:
        raise ValueError("Unknown draft operation")
    task_id = str(uuid4())
    try:
        draft_ai_task.apply_async(
            args=(str(user.pk), operation, values), task_id=task_id
        )
    except Exception as exc:
        raise DraftQueueUnavailable() from exc
    return {"id": signing.dumps([str(user.pk), task_id], salt=SALT), "status": "QUEUED"}


def draft_result(user, token):
    try:
        owner_id, task_id = signing.loads(token, salt=SALT, max_age=MAX_AGE)
    except (signing.BadSignature, ValueError, TypeError) as exc:
        raise NotFound("Draft job not found or expired.") from exc
    if owner_id != str(user.pk):
        raise NotFound("Draft job not found.")
    job = AsyncResult(task_id)
    if job.state == "SUCCESS":
        result = job.result
        if result.get("ok"):
            return {"status": "SUCCEEDED", "result": result["data"]}
        return {
            "status": "FAILED",
            "error": result.get("message", "Could not generate this draft."),
        }
    if job.state in ("FAILURE", "REVOKED"):
        return {
            "status": "FAILED",
            "error": "Could not generate this draft. Please try again.",
        }
    return {"status": "RUNNING" if job.state == "STARTED" else "QUEUED"}


def run_draft(user, operation, values):
    """Use an allowlist and reload owned resources in the worker, never a client function name."""
    from apps.videomanagement.models import Video

    if operation == "rewrite":
        from apps.videomanagement.models import Scene
        from .scenes.generation import generate_scene

        scene = Scene.objects.select_related("video__created_by").get(
            pk=values["scene_id"], video__created_by=user
        )
        return {"text": generate_scene(values["instructions"], scene)}
    if operation == "story":
        from .videos.story import draft_story

        return draft_story(user, **values)
    if operation == "cast":
        from apps.series.services.characters import draft_cast

        return {"cast": draft_cast(user, values)}
    if operation == "character":
        from apps.series.services.characters import draft_character_description

        return {"character": draft_character_description(user, values)}
    if operation == "memory":
        from apps.series.models import SeriesEpisode
        from apps.series.services.episodes import draft_episode_memory

        episode = SeriesEpisode.objects.with_script().get(
            pk=values["episode_id"], series__created_by=user
        )
        return draft_episode_memory(episode, owner=user, summary=values.get("summary"))
    if operation == "clip_search":
        from apps.clips.models import ClipProject
        from apps.clips.highlights import suggest_clips

        project = ClipProject.objects.get(pk=values["project_id"], created_by=user)
        project.extraction_prompt = values["prompt"]
        project.clip_count = 3
        return {"clips": suggest_clips(project)}
    if operation == "hashtags":
        from apps.clips.models import Clip
        from apps.clips.hashtags import draft_hashtags

        clip = Clip.objects.get(pk=values["clip_id"], project__created_by=user)
        return {"hashtags": draft_hashtags(clip, user)}
    video = Video.objects.get(pk=values["video_id"], created_by=user)
    if operation == "scene":
        from .scenes.generation import draft_scene

        return draft_scene(video, **values["choices"])
    if operation == "tags":
        from .videos.tags import generate_tags

        return {"tags": generate_tags(video, user)}
    if operation == "save_tags":
        from .videos.tags import generate_and_save_tags

        return {
            "tags": generate_and_save_tags(video, user=user, **values["choices"]).tags
        }
    if operation == "description":
        from .videos.youtube_metadata import youtube_description

        return {"description": youtube_description(video, user, values["mode"])}
    raise ValueError("Unknown draft operation")
