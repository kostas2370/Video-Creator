import mimetypes
from pathlib import Path, PurePosixPath
from urllib.parse import quote

from django.conf import settings
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.utils.cache import patch_vary_headers
from rest_framework.decorators import api_view

from apps.clips.protected_media import media_response
from apps.series.models import Character, VideoSeries

from .models import (
    Avatar,
    CaptionProject,
    Icon,
    Intro,
    MediaAsset,
    Music,
    MusicCatalogTrack,
    Outro,
    Scene,
    Video,
)


def authorized_file(user, name):
    owned = Q(created_by=user)
    shared = owned | Q(created_by__isnull=True)
    sources = [
        (
            Video.objects.filter(owned),
            ("output", "reference_image", "cover", "thumbnail"),
        ),
        (
            Scene.all_objects.filter(video__created_by=user),
            ("file", "voiceover", "overlay_logo"),
        ),
        (MediaAsset.objects.filter(owned), ("file",)),
        (CaptionProject.objects.filter(owned), ("source", "preview", "output")),
        (VideoSeries.objects.filter(owned), ("reference_image",)),
        (Character.objects.filter(owned), ("image", "pending_image")),
        (MusicCatalogTrack.objects.filter(approved=True), ("file",)),
        *[
            (model.objects.filter(shared), ("file",))
            for model in (Avatar, Intro, Outro, Music, Icon)
        ],
    ]
    for queryset, fields in sources:
        matches = Q()
        for field in fields:
            matches |= Q(**{field: name})
        obj = queryset.filter(matches).first()
        if obj:
            for field in fields:
                stored = getattr(obj, field)
                if stored and stored.name == name:
                    return stored
    raise Http404("Media is unavailable.")


@api_view(["GET", "HEAD"])
def protected_media(request, path):
    if "\\" in path or any(part in (".", "..") for part in path.split("/")):
        raise Http404("Media is unavailable.")
    name = "media/" + path
    if str(PurePosixPath(name)) != name:
        raise Http404("Media is unavailable.")
    field = authorized_file(request.user, name)
    if not field.storage.exists(field.name):
        raise Http404("Media is unavailable.")
    if getattr(settings, "MEDIA_ACCEL_REDIRECT", False):
        media_root = (Path(settings.MEDIA_ROOT) / "media").resolve()
        if not Path(field.path).resolve().is_relative_to(media_root):
            raise Http404("Media is unavailable.")
        response = HttpResponse(
            content_type=mimetypes.guess_type(name)[0] or "application/octet-stream"
        )
        response["X-Accel-Redirect"] = "/_protected_media/" + quote(path, safe="/")
        response["Cache-Control"] = "private, no-store"
        patch_vary_headers(response, ["Cookie", "Authorization"])
        return response
    return media_response(request, field)
