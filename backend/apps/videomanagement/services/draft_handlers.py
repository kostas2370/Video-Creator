"""Registered AI draft handlers. Defining a handler also makes it dispatchable."""

from apps.clips import hashtags as clip_hashtags
from apps.clips import highlights
from apps.clips.models import Clip, ClipProject
from apps.series.models import SeriesEpisode
from apps.series.services import characters, episodes
from apps.videomanagement.models import Scene, Video
from apps.videomanagement.services.scenes import generation as scene_generation
from apps.videomanagement.services.videos import story as video_story
from apps.videomanagement.services.videos import tags as video_tags
from apps.videomanagement.services.videos import youtube_metadata

_handlers = {}


def register(handler):
    name = handler.__name__
    if name in _handlers:
        raise ValueError(f"Draft handler already registered: {name}")
    _handlers[name] = handler
    return handler


def get_handler(name):
    try:
        return _handlers[name]
    except KeyError as exc:
        raise ValueError(f"Unknown draft handler: {name}") from exc


def owned_video(user, video_id):
    return Video.objects.get(pk=video_id, created_by=user)


@register
def story(user, *, prompt):
    return video_story.draft_story(user, prompt=prompt)


@register
def scene(user, *, video_id, choices):
    return scene_generation.draft_scene(owned_video(user, video_id), **choices)


@register
def rewrite(user, *, scene_id, instructions):
    scene = Scene.objects.select_related("video__created_by").get(
        pk=scene_id, video__created_by=user
    )
    return {"text": scene_generation.generate_scene(instructions, scene)}


@register
def cast(user, **choices):
    return {"cast": characters.draft_cast(user, choices)}


@register
def character(user, **choices):
    return {"character": characters.draft_character_description(user, choices)}


@register
def memory(user, *, episode_id, summary=None):
    episode = SeriesEpisode.objects.with_script().get(
        pk=episode_id, series__created_by=user
    )
    return episodes.draft_episode_memory(episode, owner=user, summary=summary)


@register
def tags(user, *, video_id):
    return {"tags": video_tags.generate_tags(owned_video(user, video_id), user)}


@register
def save_tags(user, *, video_id, choices):
    video = video_tags.generate_and_save_tags(
        owned_video(user, video_id), user=user, **choices
    )
    return {"tags": video.tags}


@register
def description(user, *, video_id, mode):
    return {
        "description": youtube_metadata.youtube_description(
            owned_video(user, video_id), user, mode
        )
    }


@register
def hashtags(user, *, clip_id):
    clip = Clip.objects.get(pk=clip_id, project__created_by=user)
    return {"hashtags": clip_hashtags.draft_hashtags(clip, user)}


@register
def clip_search(user, *, project_id, prompt):
    project = ClipProject.objects.get(pk=project_id, created_by=user)
    project.extraction_prompt = prompt
    project.clip_count = 3
    return {"clips": highlights.suggest_clips(project)}
