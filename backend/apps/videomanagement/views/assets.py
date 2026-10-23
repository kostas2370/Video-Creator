from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

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
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["title"]
    pagination_class = AssetResultsPagination
    ordering = ("id",)
    serializer_class = TemplatePromptsSerializer
    queryset = TemplatePrompt.objects.all()
    permission_classes = [IsAuthenticated, IsOwnerPermission]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return TemplatePrompt.objects.none()
        if self.request.user.is_superuser:
            return TemplatePrompt.objects.order_by("id")

        return TemplatePrompt.objects.filter(created_by=self.request.user).order_by(
            "id"
        )


class VoiceView(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name"]
    filterset_fields = ["is_cloned"]
    pagination_class = AssetResultsPagination
    ordering = ("id",)
    serializer_class = VoiceModelSerializer
    queryset = VoiceModel.objects.all()
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnlyPermission]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return VoiceModel.objects.none()
        if self.action == "destroy":
            return VoiceModel.objects.filter(created_by=self.request.user).order_by(
                "id"
            )
        if self.action in ("preview", "refresh"):
            return VoiceModel.objects.filter(
                created_by=self.request.user, is_cloned=True
            ).order_by("id")
        return VoiceModel.objects.available_to(self.request.user).order_by("id")

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
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name"]

    pagination_class = AssetResultsPagination
    ordering = ("id",)
    serializer_class = AvatarSerializer
    queryset = Avatar.objects.all()
    permission_classes = [IsAuthenticated, IsOwnerPermission]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Avatar.objects.none()
        return (
            Avatar.objects.filter(created_by=self.request.user)
            .order_by("id")
            .select_related("voice")
        )


class IntroView(viewsets.ModelViewSet):
    pagination_class = AssetResultsPagination
    ordering = ("id",)
    serializer_class = IntroSerializer
    queryset = Intro.objects.all()
    permission_classes = [IsAuthenticated, IsOwnerPermission]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Intro.objects.none()
        if self.request.user.is_superuser:
            return Intro.objects.order_by("id")

        return Intro.objects.filter(created_by=self.request.user).order_by("id")

    def perform_create(self, serializer):
        serializer.instance = save_limited_clip(
            serializer.Meta.model, self.request.user, **serializer.validated_data
        )


class OutroView(viewsets.ModelViewSet):
    pagination_class = AssetResultsPagination
    ordering = ("id",)
    serializer_class = OutroSerializer
    queryset = Outro.objects.all()
    permission_classes = [IsAuthenticated, IsOwnerPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Outro.objects.none()
        if self.request.user.is_superuser:
            return Outro.objects.order_by("id")

        return Outro.objects.filter(created_by=self.request.user).order_by("id")

    def perform_create(self, serializer):
        serializer.instance = save_limited_clip(
            serializer.Meta.model, self.request.user, **serializer.validated_data
        )
