import json
import random
import re
from pathlib import Path

from django.core.files import File
from django.db.models import Q
from django.utils.text import slugify
from rest_framework.exceptions import ValidationError

from apps.videomanagement.models import Music, MusicCatalogTrack
from apps.videomanagement.services.media.music import set_music
from apps.videomanagement.utils.file_utils import stored_file_exists


CATEGORY_HINTS = {
    "educational": "educational education explain explainer tutorial science history learning lesson documentary facts study",
    "suspense": "suspense suspenseful mystery mysterious thriller tension crime detective investigation dramatic",
    "fun": "fun funny happy cheerful comedy playful upbeat humor celebration friendship kids children",
    "horror": "horror scary terrifying haunted ghost creepy nightmare terror halloween",
    "commercial": "commercial advertisement advertising advert promotion promotional corporate business product marketing brand",
    "general": "general calm ambient relaxing travel nature lifestyle inspirational",
}
IGNORED_WORDS = set(
    "the and for with this that from your video music background scene title description sentence image audio copyright free royalty youtube creative commons instrumental candidate".split()
)


def words(value):
    return set(re.findall(r"[^\W_]+", value.lower())) - IGNORED_WORDS


def select_music_track(video):
    topic = words(f"{video.title} {video.genre or ''} {video.prompt.prompt}")
    context = topic | words(json.dumps(video.gpt_answer or {}, ensure_ascii=False))
    category_scores = {
        category: len(topic & set(hints.split())) * 3
        + len(context & set(hints.split()))
        for category, hints in CATEGORY_HINTS.items()
    }
    if not any(category_scores.values()):
        category_scores["general"] = 1
    tracks = [
        track
        for track in MusicCatalogTrack.objects.filter(approved=True).exclude(
            Q(file="") | Q(license_url="")
        )
        if stored_file_exists(track.file)
    ]
    if not tracks:
        raise ValidationError(
            {
                "detail": "No general music is available yet. Upload music or try again after the catalog is ready."
            }
        )
    alternatives = [
        track
        for track in tracks
        if not video.music_id
        or video.music.name not in (track.title, slugify(track.title)[:100])
    ]
    tracks = alternatives or tracks

    def score(track):
        return (
            category_scores.get(track.category, 0),
            len(context & words(f"{track.title} {' '.join(track.tags)}")),
        )

    best = max(map(score, tracks))
    return random.choice([track for track in tracks if score(track) == best])


def set_catalog_music(video, track):
    with track.file.open("rb") as source:
        name = (slugify(track.title)[:100] or "catalog-music") + Path(
            track.file.name
        ).suffix
        return set_music(video, File(source, name=name))


def create_catalog_music(track, *, user):
    music = Music(created_by=user, name=track.title[:140])
    with track.file.open("rb") as source:
        music.file.save(track.file.name.rsplit("/", 1)[-1], File(source), save=False)
    try:
        music.save()
    except Exception:
        music.file.storage.delete(music.file.name)
        raise
    return music
