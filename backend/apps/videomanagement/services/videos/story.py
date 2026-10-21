"""Draft stories and create editable narrated gameplay projects."""

import json
import re

from django.db import transaction
from rest_framework.exceptions import APIException, ValidationError

from apps.videomanagement import tasks
from apps.videomanagement.integrations.llm import get_update_sentence
from apps.videomanagement.models import SceneImage
from apps.videomanagement.schemas.drafts import StoryDraftResultSerializer
from apps.videomanagement.services.scenes.jobs import QueueUnavailable, queue_scene_job
from apps.videomanagement.services.scenes.narration import make_scene_speech
from apps.videomanagement.services.videos.manual import create_manual_video


def draft_story(user, prompt):
    instructions = (
        "Create a story draft following the user's prompt below. "
        "Return ONLY a JSON object with title (at most 50 characters) and story "
        "(plain narration only, no headings, scene directions, hashtags, or markdown). "
        "Use the language requested by the user, otherwise the language of their prompt. "
        "The story must fit the editor's limit of 2000 characters.\nUser prompt: "
        + json.dumps(prompt, ensure_ascii=False)
    )
    reply = get_update_sentence(instructions, user=user)
    try:
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", reply.strip())
        result = json.loads(cleaned)
        serializer = StoryDraftResultSerializer(data=result)
        serializer.is_valid(raise_exception=True)
    except (ValueError, TypeError, AttributeError, ValidationError) as exc:
        raise APIException(
            "AI returned an invalid story draft. Please try again."
        ) from exc
    return dict(serializer.validated_data)


def create_story_video(user, *, title, story, gameplay, voice_id, subtitles=True):
    """Persist an editable story and muted gameplay before queuing narration."""
    visual = None
    try:
        with transaction.atomic():
            video = create_manual_video(
                user,
                title=title,
                video_format="PORTRAIT",
                platform="TIKTOK",
                subtitles=subtitles,
                narration=True,
                creation_mode="STORY",
                loop_visual=True,
            )
            video.voice_model = voice_id
            video.save(update_fields=["voice_model"])
            scene = make_scene_speech(video, story, False, narrate=False)
            visual = SceneImage(scene=scene, file=gameplay, with_audio=False)
            visual.save()
    except Exception:
        if visual:
            visual.discard_upload()
        raise
    return video, scene


def create_story_project(user, **choices):
    video, scene = create_story_video(user, **choices)
    warning = None
    try:
        queue_scene_job(scene, tasks.update_scene_task, scene.text)
    except QueueUnavailable:
        warning = "Project saved. Narration could not be queued; use Retry narration in the editor."
    video.refresh_from_db()
    return video, warning
