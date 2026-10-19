from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.videomanagement.serializers.tags import (
    GenerateVideoTagsSerializer,
    SaveVideoTagsSerializer,
)
from apps.videomanagement.services.videos.tags import generate_and_save_tags, save_tags
from apps.videomanagement.throttling import TagGenerationRateThrottle


class VideoTagsMixin:
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
        video = generate_and_save_tags(
            video, user=request.user, **serializer.validated_data
        )
        return Response({"tags": video.tags})
