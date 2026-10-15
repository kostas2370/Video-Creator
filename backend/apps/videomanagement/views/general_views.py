from rest_framework import mixins, viewsets
from rest_framework.response import Response
from rest_framework.filters import OrderingFilter, SearchFilter

from django_filters.rest_framework import DjangoFilterBackend
from ..permissions import IsOwnerOrReadOnlyPermission, IsOwnerPermission
from rest_framework.permissions import IsAuthenticated

from ..models import (
    TemplatePrompt,
    Outro,
    Intro,
    VoiceModel,
    Avatar,
    SceneImage,
)
from ..serializers.models import (
    TemplatePromptsSerializer,
    IntroSerializer,
    OutroSerializer,
    VoiceModelSerializer,
    AvatarSerializer,
    SceneImageSerializer,
)
from ..services.asset_limits import save_limited_clip
from ..services.editing import editable_video
from ..paginator import AssetResultsPagination


class SceneImageView(viewsets.GenericViewSet):
    queryset = SceneImage.objects.all()
    serializer_class = SceneImageSerializer
    permission_classes = [IsAuthenticated, IsOwnerPermission]

    def destroy(self, request, pk):
        obj = self.get_object()
        with editable_video(obj.scene.video_id):
            obj.file = None
            obj.save()

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
        if self.request.user.is_superuser:
            return TemplatePrompt.objects.order_by("id")

        return TemplatePrompt.objects.filter(created_by=self.request.user).order_by("id")


class VoiceView(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name"]
    pagination_class = AssetResultsPagination
    ordering = ("id",)
    serializer_class = VoiceModelSerializer
    queryset = VoiceModel.objects.all()
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnlyPermission]

    def get_queryset(self):
        return VoiceModel.objects.available_to(self.request.user).order_by("id")


class AvatarView(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name"]

    pagination_class = AssetResultsPagination
    ordering = ("id",)
    serializer_class = AvatarSerializer
    queryset = Avatar.objects.all()
    permission_classes = [IsAuthenticated, IsOwnerPermission]

    def get_queryset(self):
        return Avatar.objects.filter(created_by=self.request.user).order_by("id").select_related(
            "voice"
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
        if self.request.user.is_superuser:
            return Intro.objects.order_by("id")

        return Intro.objects.filter(created_by=self.request.user).order_by("id")

    def perform_create(self, serializer):
        save_limited_clip(serializer, self.request.user)


class OutroView(viewsets.ModelViewSet):
    pagination_class = AssetResultsPagination
    ordering = ("id",)
    serializer_class = OutroSerializer
    queryset = Outro.objects.all()
    permission_classes = [IsAuthenticated, IsOwnerPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name"]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Outro.objects.order_by("id")

        return Outro.objects.filter(created_by=self.request.user).order_by("id")

    def perform_create(self, serializer):
        save_limited_clip(serializer, self.request.user)
