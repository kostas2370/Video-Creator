"""Celery tasks for AI writing requests."""

from celery import shared_task
from django.contrib.auth import get_user_model

from apps.clips import hashtags as clip_hashtags
from apps.clips import highlights
from apps.clips.models import Clip, ClipProject
from apps.series.models import SeriesEpisode
from apps.series.services import characters, episodes
from apps.videomanagement.models import Scene, Video
from apps.videomanagement.serializers.ideas import (
    IdeaResultSerializer,
    PromptResultSerializer,
)
from apps.videomanagement.services.scenes import generation as scene_generation
from apps.videomanagement.services.scenes.starting_frame_review import review_starting_frame
from apps.videomanagement.services.videos import story as video_story
from apps.videomanagement.services.videos.ideas import creative_reply
from apps.videomanagement.services.videos import tags as video_tags
from apps.videomanagement.services.videos import youtube_metadata
from apps.videomanagement.services.videos.storyboard_revision import revise_storyboard
from apps.videomanagement.utils.prompt_utils import build_ideas_prompt, build_prompt_rewrite


def load_user(user_id):
    return get_user_model().objects.get(pk=user_id)


def owned_video(user, video_id):
    return Video.objects.get(pk=video_id, created_by=user)


@shared_task(soft_time_limit=570, time_limit=600, expires=86400)
def draft_story_task(user_id, *, prompt):
    user = load_user(user_id)
    return video_story.draft_story(user, prompt=prompt)


@shared_task(soft_time_limit=570, time_limit=600, expires=86400)
def generate_ideas_task(user_id, *, gpt_model="", **brief):
    return creative_reply(
        load_user(user_id),
        prompt=build_ideas_prompt(brief),
        serializer_class=IdeaResultSerializer,
        error_message="AI returned invalid ideas. Please try again.",
        gpt_model=gpt_model,
    )


@shared_task(soft_time_limit=570, time_limit=600, expires=86400)
def rewrite_prompt_task(user_id, *, gpt_model="", **brief):
    return creative_reply(
        load_user(user_id),
        prompt=build_prompt_rewrite(brief),
        serializer_class=PromptResultSerializer,
        error_message="AI returned an invalid rewrite. Please try again.",
        gpt_model=gpt_model,
    )


@shared_task(soft_time_limit=570, time_limit=600, expires=86400)
def revise_storyboard_task(user_id, *, video_id, **choices):
    return revise_storyboard(owned_video(load_user(user_id), video_id), **choices)


@shared_task(soft_time_limit=570, time_limit=600, expires=86400)
def draft_scene_task(user_id, *, video_id, choices):
    user = load_user(user_id)
    return scene_generation.draft_scene(owned_video(user, video_id), **choices)


@shared_task(soft_time_limit=570, time_limit=600, expires=86400)
def rewrite_scene_task(user_id, *, scene_id, instructions):
    user = load_user(user_id)
    scene = Scene.objects.select_related("video__created_by").get(
        pk=scene_id, video__created_by=user
    )
    return {"text": scene_generation.generate_scene(instructions, scene)}


@shared_task(soft_time_limit=570, time_limit=600, expires=86400)
def review_starting_frame_task(user_id, *, scene_id, source_key):
    user = load_user(user_id)
    scene = Scene.objects.select_related("video__created_by", "starting_asset").get(
        pk=scene_id, video__created_by=user
    )
    return review_starting_frame(scene, source_key)


@shared_task(soft_time_limit=570, time_limit=600, expires=86400)
def draft_cast_task(user_id, **choices):
    user = load_user(user_id)
    return {"cast": characters.draft_cast(user, choices)}


@shared_task(soft_time_limit=570, time_limit=600, expires=86400)
def draft_character_task(user_id, **choices):
    user = load_user(user_id)
    return {"character": characters.draft_character_description(user, choices)}


@shared_task(soft_time_limit=570, time_limit=600, expires=86400)
def draft_memory_task(user_id, *, episode_id, summary=None):
    user = load_user(user_id)
    episode = SeriesEpisode.objects.with_script().get(
        pk=episode_id, series__created_by=user
    )
    return episodes.draft_episode_memory(episode, owner=user, summary=summary)


@shared_task(soft_time_limit=570, time_limit=600, expires=86400)
def draft_tags_task(user_id, *, video_id):
    user = load_user(user_id)
    return {"tags": video_tags.generate_tags(owned_video(user, video_id), user)}


@shared_task(soft_time_limit=570, time_limit=600, expires=86400)
def generate_tags_task(user_id, *, video_id, choices):
    user = load_user(user_id)
    video = video_tags.generate_and_save_tags(
        owned_video(user, video_id), user=user, **choices
    )
    return {"tags": video.tags}


@shared_task(soft_time_limit=570, time_limit=600, expires=86400)
def draft_description_task(user_id, *, video_id, mode):
    user = load_user(user_id)
    return {
        "description": youtube_metadata.youtube_description(
            owned_video(user, video_id), user, mode
        )
    }


@shared_task(soft_time_limit=570, time_limit=600, expires=86400)
def draft_hashtags_task(user_id, *, clip_id):
    user = load_user(user_id)
    clip = Clip.objects.get(pk=clip_id, project__created_by=user)
    return {"hashtags": clip_hashtags.draft_hashtags(clip, user)}


@shared_task(soft_time_limit=570, time_limit=600, expires=86400)
def search_transcript_task(user_id, *, project_id, prompt):
    user = load_user(user_id)
    project = ClipProject.objects.get(pk=project_id, created_by=user)
    project.extraction_prompt = prompt
    project.clip_count = 3
    return {"clips": highlights.suggest_clips(project)}
