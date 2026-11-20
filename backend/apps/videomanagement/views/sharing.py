from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.clips.protected_media import media_response
from apps.videomanagement.models import Video, VideoShare


class ShareOptionsSerializer(serializers.Serializer):
    expires_in_days = serializers.ChoiceField(
        choices=[1, 7, 30], allow_null=True, default=None
    )


def share_details(share):
    active = share is not None and share.active
    return {
        "active": active,
        "path": f"/share/{share.token}/" if active else None,
        "expires_at": share.expires_at if active else None,
    }


class VideoShareMixin:
    @action(detail=True, methods=["GET", "POST", "DELETE"], url_path="share")
    def share(self, request, pk=None):
        video = self.get_object()
        if request.method == "GET":
            return Response(
                share_details(VideoShare.objects.filter(video=video).first()),
                headers={"Cache-Control": "no-store"},
            )

        options = ShareOptionsSerializer(data=request.data)
        if request.method == "POST":
            options.is_valid(raise_exception=True)
        with transaction.atomic():
            # Serialize creation and revocation for this video, including the first link.
            video = Video.objects.select_for_update().get(pk=video.pk)
            shares = VideoShare.objects.filter(video=video)
            if request.method == "DELETE":
                shares.delete()
                return Response(status=204)
            if not video.output:
                raise ValidationError("Export your video before creating a share link.")
            share = shares.first()
            if share is None or not share.active:
                shares.delete()
                days = options.validated_data["expires_in_days"]
                share = VideoShare.objects.create(
                    video=video,
                    expires_at=timezone.now() + timedelta(days=days) if days else None,
                )
            return Response(share_details(share), headers={"Cache-Control": "no-store"})


class PublicVideoShareView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    http_method_names = ["get", "head", "options"]

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "private, no-store"
        response["X-Robots-Tag"] = "noindex, nofollow"
        response["Referrer-Policy"] = "no-referrer"
        return response

    def get(self, request, token, media=False):
        share = get_object_or_404(
            VideoShare.objects.select_related("video")
            .filter(
                Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()),
            )
            .exclude(video__output="")
            .exclude(video__output__isnull=True),
            token=token,
        )
        video = share.video
        if media:
            return media_response(request, video.output)

        tags = list(
            dict.fromkeys(
                tag
                for group in video.tags.values()
                if isinstance(group, list)
                for tag in group
                if isinstance(tag, str) and tag.strip()
            )
        )
        return Response(
            {
                "title": video.title,
                "description": video.description,
                "tags": tags,
                "media_url": request.build_absolute_uri(
                    reverse("shared-video-media", args=[token])
                ),
            }
        )
