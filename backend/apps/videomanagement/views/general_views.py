from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.filters import OrderingFilter, SearchFilter

from django_filters.rest_framework import DjangoFilterBackend
from ..permissions import IsOwnerOrReadOnlyPermission, IsOwnerPermission
from rest_framework.permissions import IsAuthenticated

from ..models import (
    TemplatePrompt,
    Outro,
    Intro,
    Music,
    VoiceModel,
    Avatar,
    SceneImage,
    Video,
    VideoType,
)
from ..serializers import (
    TemplatePromptsSerializer,
    IntroSerializer,
    OutroSerializer,
    MusicSerializer,
    VoiceModelSerializer,
    AvatarSerializer,
    SceneImageSerializer,
)


class SceneImageView(viewsets.GenericViewSet):
    queryset = SceneImage.objects.all()
    serializer_class = SceneImageSerializer
    permission_classes = [IsAuthenticated, IsOwnerPermission]

    def destroy(self, request, pk):
        obj = self.get_object()
        video = Video.objects.filter(prompt_id=obj.scene.prompt_id).first()

        if video is None:
            return Response(
                {"message": "The video this image belongs to is gone"}, status=404
            )

        if video.video_type == VideoType.AI:
            obj.file = None
            obj.save()

        if video.video_type == VideoType.TWITCH:
            obj.scene.delete()

        return Response(status=204)


class TemplatePromptView(viewsets.ModelViewSet):
    serializer_class = TemplatePromptsSerializer
    queryset = TemplatePrompt.objects.all()
    permission_classes = [IsAuthenticated, IsOwnerPermission]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return TemplatePrompt.objects.all()

        return TemplatePrompt.objects.filter(created_by=self.request.user)


class MusicView(viewsets.ModelViewSet):
    serializer_class = MusicSerializer
    queryset = Music.objects.all()
    permission_classes = [IsAuthenticated, IsOwnerPermission]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Music.objects.all()

        return Music.objects.filter(created_by=self.request.user)


class VoiceView(viewsets.ModelViewSet):
    serializer_class = VoiceModelSerializer
    queryset = VoiceModel.objects.all()
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnlyPermission]

    def get_queryset(self):
        return VoiceModel.available_to(self.request.user)


class AvatarView(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name"]

    serializer_class = AvatarSerializer
    queryset = Avatar.objects.all()
    permission_classes = [IsAuthenticated, IsOwnerPermission]

    def get_queryset(self):
        return Avatar.objects.filter(created_by=self.request.user).select_related(
            "voice"
        )


class IntroView(viewsets.ModelViewSet):
    serializer_class = IntroSerializer
    queryset = Intro.objects.all()
    permission_classes = [IsAuthenticated, IsOwnerPermission]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name"]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Intro.objects.all()

        return Intro.objects.filter(created_by=self.request.user)


class OutroView(viewsets.ModelViewSet):
    serializer_class = OutroSerializer
    queryset = Outro.objects.all()
    permission_classes = [IsAuthenticated, IsOwnerPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name"]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Outro.objects.all()

        return Outro.objects.filter(created_by=self.request.user)
