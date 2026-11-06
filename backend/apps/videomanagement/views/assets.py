from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.videomanagement.filters import (
    AvatarFilter,
    IntroFilter,
    OutroFilter,
    TemplatePromptFilter,
    VoiceFilter,
)
from apps.videomanagement.models import (
    Avatar,
    Intro,
    Outro,
    SceneImage,
    TemplatePrompt,
    VoiceModel,
)
from apps.videomanagement.paginator import AssetResultsPagination
from apps.videomanagement.permissions import (
    IsOwnerOrReadOnlyPermission,
    IsOwnerPermission,
)
from apps.videomanagement.serializers.custom_voices import CloneVoiceSerializer
from apps.videomanagement.serializers.models import (
    AvatarSerializer,
    IntroSerializer,
    OutroSerializer,
    SceneImageSerializer,
    TemplatePromptsSerializer,
    VoiceModelSerializer,
)
from apps.videomanagement.services.media.assets import save_limited_clip
from apps.videomanagement.services.scenes.editing import clear_scene_image
from apps.videomanagement.services.voices.cloning import (
    create_clone,
    delete_clone,
    preview_clone,
    refresh_clone,
)
from apps.videomanagement.throttling import CloneVoiceThrottle, VoicePreviewThrottle


class SceneImageView(viewsets.GenericViewSet):
    queryset = SceneImage.objects.select_related("scene__video")
    serializer_class = SceneImageSerializer
    permission_classes = [IsAuthenticated, IsOwnerPermission]

    def destroy(self, request, pk):
        clear_scene_image(self.get_object())
        return Response(status=204)


class TemplatePromptView(viewsets.ModelViewSet):
    filterset_class = TemplatePromptFilter
    filter_backends = [DjangoFilterBackend]
    pagination_class = AssetResultsPagination
    serializer_class = TemplatePromptsSerializer
    queryset = TemplatePrompt.objects.order_by("id")
    permission_classes = [IsAuthenticated, IsOwnerPermission]


class VoiceView(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    filter_backends = [DjangoFilterBackend]
    filterset_class = VoiceFilter
    pagination_class = AssetResultsPagination
    serializer_class = VoiceModelSerializer
    queryset = VoiceModel.objects.all()
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnlyPermission]

    def get_serializer_class(self):
        return (
            CloneVoiceSerializer
            if self.action == "clone"
            else super().get_serializer_class()
        )

    @action(detail=False, methods=["post"], throttle_classes=[CloneVoiceThrottle])
    def clone(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        voice = create_clone(request.user, data["name"], data["file"])
        return Response(self.get_serializer(voice).data, status=201)

    @action(detail=True, methods=["post"], throttle_classes=[VoicePreviewThrottle])
    def preview(self, request, pk=None):
        response = HttpResponse(
            preview_clone(request.user, self.get_object()), content_type="audio/mpeg"
        )
        response["Cache-Control"] = "private, no-store"
        return response

    @action(detail=True, methods=["post"], throttle_classes=[VoicePreviewThrottle])
    def refresh(self, request, pk=None):
        voice = self.get_object()
        refresh_clone(request.user, voice)
        return Response(self.get_serializer(voice).data)

    def perform_destroy(self, instance):
        if instance.is_cloned:
            delete_clone(self.request.user, instance)
        else:
            instance.delete()


class AvatarView(viewsets.ModelViewSet):
    filterset_class = AvatarFilter
    filter_backends = [DjangoFilterBackend]

    pagination_class = AssetResultsPagination
    serializer_class = AvatarSerializer
    queryset = Avatar.objects.select_related("voice").order_by("id")
    permission_classes = [IsAuthenticated, IsOwnerPermission]


class LimitedClipView(viewsets.ModelViewSet):
    pagination_class = AssetResultsPagination
    permission_classes = [IsAuthenticated, IsOwnerPermission]
    filter_backends = [DjangoFilterBackend]

    def perform_create(self, serializer):
        serializer.instance = save_limited_clip(
            serializer.Meta.model, self.request.user, **serializer.validated_data
        )


class IntroView(LimitedClipView):
    filterset_class = IntroFilter
    serializer_class = IntroSerializer
    queryset = Intro.objects.order_by("id")


class OutroView(LimitedClipView):
    filterset_class = OutroFilter
    serializer_class = OutroSerializer
    queryset = Outro.objects.order_by("id")
