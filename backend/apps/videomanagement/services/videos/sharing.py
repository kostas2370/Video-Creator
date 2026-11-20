from datetime import timedelta

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.videomanagement.exceptions import ShareLinkExpired
from apps.videomanagement.models import Video, VideoShare


@transaction.atomic
def create_video_share(video, *, expires_in_days):
    # Lock the parent to serialize creation, including when no share exists yet.
    video = Video.objects.select_for_update().get(pk=video.pk)
    if not video.output:
        raise ValidationError("Export your video before creating a share link.")
    share = VideoShare.objects.filter(video=video).first()
    if share is not None and share.active:
        return share
    VideoShare.objects.filter(video=video).delete()
    return VideoShare.objects.create(
        video=video,
        expires_at=timezone.now() + timedelta(days=expires_in_days)
        if expires_in_days
        else None,
    )


@transaction.atomic
def revoke_video_share(video):
    Video.objects.select_for_update().get(pk=video.pk)
    VideoShare.objects.filter(video=video).delete()


def get_shared_video(token):
    share = get_object_or_404(
        VideoShare.objects.select_related("video")
        .only(
            "expires_at",
            "video__title",
            "video__description",
            "video__tags",
            "video__output",
        )
        .exclude(video__output="")
        .exclude(video__output__isnull=True),
        token=token,
    )
    if not share.active:
        raise ShareLinkExpired
    return share.video
