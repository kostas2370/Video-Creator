from pathlib import Path

from django.core.files import File
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from ..models import MediaAsset, Video, SceneImage
from ..paginator import AssetResultsPagination
from ..permissions import IsOwnerPermission
from ..serializers.library import MediaAssetSerializer, UseMediaSerializer
from ..services.editing import editable_video, changed
from ..services.manual import add_manual_scene, set_music
from ..utils.file_utils import stored_file_exists


class MediaAssetView(viewsets.ModelViewSet):
    queryset = MediaAsset.objects.all()
    serializer_class = MediaAssetSerializer
    permission_classes = [IsAuthenticated, IsOwnerPermission]
    pagination_class = AssetResultsPagination
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        rows = MediaAsset.objects.filter(created_by=self.request.user)
        term = self.request.query_params.get("search", "").strip()[:100]
        if term:
            rows = rows.filter(Q(title__icontains=term) | Q(tags__icontains=term))
        kind = self.request.query_params.get("kind")
        if kind == "VISUAL":
            rows = rows.filter(kind__in=("IMAGE", "VIDEO"))
        elif kind:
            rows = rows.filter(kind=kind)
        return rows

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_destroy(self, instance):
        file = instance.file
        instance.delete()
        transaction.on_commit(lambda: file.storage.delete(file.name), robust=True)

    @action(detail=True, methods=["POST"])
    def use(self, request, pk=None):
        asset = self.get_object()
        serializer = UseMediaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        video = get_object_or_404(Video.objects.for_user(request.user), pk=data["video_id"])
        if not stored_file_exists(asset.file):
            raise ValidationError("This library file is missing. Upload it again.")
        purpose = data["purpose"]
        if (purpose == "music") != (asset.kind == "AUDIO"):
            raise ValidationError("Use audio as background music, and images or clips as scene visuals.")
        scene = None
        with asset.file.open("rb") as source:
            upload = File(source, name=Path(asset.file.name).name)
            if purpose == "music":
                set_music(video, upload)
            elif purpose == "new_scene":
                with editable_video(video.pk) as locked:
                    if data.get("position", 1) > locked.scenes.count() + 1:
                        raise ValidationError({"position": "Choose a position within the video."})
                    scene = add_manual_scene(locked, image=upload, **{key: data[key] for key in ("text", "duration", "position", "with_audio") if key in data})
            else:
                if not data.get("scene_id"):
                    raise ValidationError({"scene_id": "Choose a scene to replace its visual."})
                with editable_video(video.pk) as locked:
                    scene = get_object_or_404(locked.scenes.select_for_update(), pk=data["scene_id"])
                    image = scene.scene_images.first()
                    old_file = image.file if image else None
                    if image:
                        image.file = upload
                        image.with_audio = data["with_audio"]
                        image.prompt = ""
                        image.save()
                    else:
                        SceneImage.objects.create(scene=scene, file=upload, with_audio=data["with_audio"])
                    changed(locked)
                    if old_file:
                        transaction.on_commit(lambda: old_file.storage.delete(old_file.name), robust=True)
        return Response({"video_id": str(video.pk), "scene_id": str(scene.pk) if scene else None})
