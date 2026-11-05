from apps.videomanagement.services.draft_jobs import draft_response
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import serializers

from apps.videomanagement.services.videos.youtube_metadata import youtube_description

from apps.videomanagement.serializers.tags import (
    GenerateVideoTagsSerializer,
    SaveVideoTagsSerializer,
    SaveVideoDetailsSerializer,
)
from apps.videomanagement.services.videos.tags import (
    generate_and_save_tags,
    save_tags,
    generate_tags,
    save_details,
)
from apps.videomanagement.throttling import TagGenerationRateThrottle


class YouTubeDescriptionSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=["generate", "template", "timestamps"])


class VideoTagsMixin:
    @swagger_auto_schema(request_body=SaveVideoDetailsSerializer)
    @action(detail=True, methods=["PATCH"])
    def details(self, request, pk=None):
        video = self.get_object()
        serializer = SaveVideoDetailsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(save_details(video, **serializer.validated_data))

    @action(detail=True, methods=["POST"], throttle_classes=[TagGenerationRateThrottle])
    def draft_tags(self, request, pk=None):
        video = self.get_object()
        return draft_response(
            request,
            "tags",
            {"video_id": str(video.pk)},
            lambda: {"tags": generate_tags(video, request.user)},
        )

    @swagger_auto_schema(request_body=YouTubeDescriptionSerializer)
    @action(detail=True, methods=["POST"], throttle_classes=[TagGenerationRateThrottle])
    def youtube_description(self, request, pk=None):
        video = self.get_object()
        serializer = YouTubeDescriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return draft_response(
            request,
            "description",
            {"video_id": str(video.pk), "mode": serializer.validated_data["mode"]},
            lambda: {
                "description": youtube_description(
                    video, request.user, serializer.validated_data["mode"]
                )
            },
        )

    @swagger_auto_schema(request_body=SaveVideoTagsSerializer)
    @action(detail=True, methods=["PATCH"])
    def tags(self, request, pk=None):
        video = self.get_object()
        serializer = SaveVideoTagsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        video = save_tags(video, **serializer.validated_data)
        return Response({"tags": video.tags})

    @swagger_auto_schema(request_body=GenerateVideoTagsSerializer)
    @action(detail=True, methods=["POST"], throttle_classes=[TagGenerationRateThrottle])
    def generate_tags(self, request, pk=None):
        video = self.get_object()
        serializer = GenerateVideoTagsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return draft_response(
            request,
            "save_tags",
            {"video_id": str(video.pk), "choices": dict(serializer.validated_data)},
            lambda: {
                "tags": generate_and_save_tags(
                    video, user=request.user, **serializer.validated_data
                ).tags
            },
        )
