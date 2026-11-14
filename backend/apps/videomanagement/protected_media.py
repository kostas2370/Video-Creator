import mimetypes
from pathlib import Path, PurePosixPath
from urllib.parse import quote

from django.conf import settings
from django.db.models import Case, CharField, F, Q, Value, When
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
    # Select only the matching source and field, without loading model rows or
    # issuing a separate database round trip for each possible owner.
    lookups = []
    for index, (queryset, fields) in enumerate(sources):
        matches = Q()
        for field in fields:
            matches |= Q(**{field: name})
        lookups.append(
            queryset.filter(matches)
            .order_by()
            .annotate(
                media_source=Value(index),
                media_field=Case(
                    *[When(**{field: name}, then=Value(field)) for field in fields]
                ),
                media_name=Case(
                    *[When(**{field: name}, then=F(field)) for field in fields],
                    output_field=CharField(),
                ),
            )
            .values_list("media_source", "media_field", "media_name")
        )
    match = next(iter(lookups[0].union(*lookups[1:], all=True)[:1]), None)
    # MySQL may compare names case-insensitively; filesystem names must still
    # match exactly so another user's differently cased file cannot be served.
    if match is None or match[2] != name:
        raise Http404("Media is unavailable.")
    source, field_name, _ = match
    field = sources[source][0].model._meta.get_field(field_name)
    return field.attr_class(None, field, name)


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
