from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.videomanagement import draft_tasks
from apps.videomanagement.serializers.tags import (
    GenerateVideoTagsSerializer,
    SaveVideoDetailsSerializer,
    SaveVideoTagsSerializer,
)
from apps.videomanagement.services.draft_jobs import queue_draft
from apps.videomanagement.services.videos.tags import (
    save_details,
    save_tags,
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
        return Response(
            queue_draft(
                request.user, draft_tasks.draft_tags_task, video_id=str(video.pk)
            ),
            status=202,
            headers={"Cache-Control": "no-store"},
        )

    @swagger_auto_schema(request_body=YouTubeDescriptionSerializer)
    @action(detail=True, methods=["POST"], throttle_classes=[TagGenerationRateThrottle])
    def youtube_description(self, request, pk=None):
        video = self.get_object()
        serializer = YouTubeDescriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            queue_draft(
                request.user,
                draft_tasks.draft_description_task,
                video_id=str(video.pk),
                mode=serializer.validated_data["mode"],
            ),
            status=202,
            headers={"Cache-Control": "no-store"},
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
        return Response(
            queue_draft(
                request.user,
                draft_tasks.generate_tags_task,
                video_id=str(video.pk),
                choices=dict(serializer.validated_data),
            ),
            status=202,
            headers={"Cache-Control": "no-store"},
        )
