from django.shortcuts import get_object_or_404
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ..serializers.overlays import SceneOverlaysSerializer
from ..serializers.scene_captions import SceneCaptionsSerializer
from ..services.scene_captions import scene_caption_data, update_scene_captions
from ..services.overlays import update_overlays
from ..serializers.requests import ManualTextSerializer
from ..models import Scene, SceneImage, VideoType
from ..schema import SceneImageUploadSchema
from ..tasks import update_scene_task, rewrite_scene_task, generate_scene_image_task
from ..serializers.models import SceneSerializer
from ..services.scene_jobs import queue_scene_job, scene_job_result
from ..services.editing import editable_video, changed
from ..serializers.requests import SceneJobQuerySerializer
from ..services.editing import update_scene_transition, update_scene_timing, update_scene_motion
from ..serializers.requests import (
    ChangeSceneImageSerializer,
    GenerateSceneImageSerializer,
    SceneImageQuerySerializer,
    SceneUpdateSerializer,
    SceneTransitionSerializer,
    SceneTimingSerializer,
    SceneMotionSerializer,
)
from ..permissions import IsOwnerPermission


from ..serializers.audio import SceneAudioSerializer, VoiceoverUploadSerializer
from ..services.audio_editing import update_audio, save_voiceover, audio_waveform


class SceneView(viewsets.GenericViewSet):
    serializer_class = SceneSerializer
    queryset = Scene.objects.all()
    permission_classes = [
        IsAuthenticated,
        IsOwnerPermission,
    ]

    def get_serializer_class(self):
        if self.action == "partial_update" and not getattr(self, "swagger_fake_view", False):
            if self.get_object().video.video_type == VideoType.MANUAL:
                return ManualTextSerializer
        return {
            "captions": SceneCaptionsSerializer,
            "overlays": SceneOverlaysSerializer,
            "audio": SceneAudioSerializer,
            "voiceover": VoiceoverUploadSerializer,
            "motion": SceneMotionSerializer,
            "timing": SceneTimingSerializer,
            "transition": SceneTransitionSerializer,
            "partial_update": SceneUpdateSerializer,
            "generate": SceneUpdateSerializer,
            "change_image_scene": ChangeSceneImageSerializer,
            "generate_image_scene": GenerateSceneImageSerializer,
        }.get(self.action, super().get_serializer_class())

    def get_permissions(self):
        return super().get_permissions()

    @action(detail=True, methods=["GET", "PATCH"])
    def captions(self, request, pk=None):
        scene = self.get_object()
        if request.method == "GET":
            return Response(scene_caption_data(scene))
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(update_scene_captions(scene, **serializer.validated_data))

    def get_parsers(self):
        # DRF sets self.action after parsers; resolve the route from the raw request.
        action = getattr(self, "action", None) or getattr(self, "action_map", {}).get(
            self.request.method.lower()
        )
        parsers = {
            "overlays": (JSONParser, MultiPartParser, FormParser),
            "voiceover": (MultiPartParser, FormParser),
            "change_image_scene": (MultiPartParser, FormParser, JSONParser),
        }.get(action)
        return [parser() for parser in parsers] if parsers else super().get_parsers()

    @swagger_auto_schema(responses={200: SceneSerializer})
    @action(detail=True, methods=["PATCH"])
    def overlays(self, request, pk=None):
        scene = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scene = update_overlays(scene, serializer.validated_data)
        return Response(SceneSerializer(scene, context=self.get_serializer_context()).data)

    @swagger_auto_schema(request_body=SceneAudioSerializer)
    @action(detail=True, methods=["PATCH"])
    def audio(self, request, pk=None):
        scene = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(SceneSerializer(update_audio(scene, serializer.validated_data)).data)

    @action(detail=True, methods=["POST", "DELETE"])
    def voiceover(self, request, pk=None):
        scene = self.get_object()
        upload = None
        if request.method == "POST":
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            upload = serializer.validated_data["file"]
        return Response(SceneSerializer(save_voiceover(scene, upload)).data)

    @action(detail=True, methods=["GET"])
    def waveform(self, request, pk=None):
        return Response(audio_waveform(self.get_object()), headers={"Cache-Control": "private, no-store"})

    @swagger_auto_schema(request_body=SceneMotionSerializer)
    @action(detail=True, methods=["PATCH"])
    def motion(self, request, pk=None):
        owned_scene = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scene = update_scene_motion(owned_scene, **serializer.validated_data)
        return Response(SceneSerializer(scene).data)

    @swagger_auto_schema(request_body=SceneTimingSerializer)
    @action(detail=True, methods=["PATCH"])
    def timing(self, request, pk=None):
        owned_scene = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scene = update_scene_timing(owned_scene, **serializer.validated_data)
        return Response(SceneSerializer(scene).data)

    @swagger_auto_schema(request_body=SceneTransitionSerializer)
    @action(detail=True, methods=["PATCH"])
    def transition(self, request, pk=None):
        owned_scene = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scene = update_scene_transition(owned_scene, **serializer.validated_data)
        return Response({"transition_after": scene.transition_after, "transition_duration": scene.transition_duration})

    @swagger_auto_schema(
        request_body=SceneUpdateSerializer,
        operation_description="This API updates the text of a scene and regenerates their dialogue "
        "with the new text",
    )
    def partial_update(self, request, pk=None):
        instance = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if instance.video.video_type == VideoType.MANUAL:
            with editable_video(instance.video_id) as video:
                instance.text = serializer.validated_data["text"]
                instance.save(update_fields=["text"])
                changed(video)
            return Response(SceneSerializer(instance).data)
        if not serializer.validated_data["text"].strip():
            return Response({"detail": "Add dialogue for this scene."}, status=400)
        operation = queue_scene_job(
            instance, update_scene_task, serializer.validated_data["text"],
        )
        return Response(operation, status=status.HTTP_202_ACCEPTED)

    @swagger_auto_schema(
        request_body=SceneUpdateSerializer,
        operation_description="This API sends the dialogue into gpt and changes it depending on the "
        "prompt user sends of th of a scene and regenerates their dialogue "
        "with the new text",
    )
    @action(detail=True, methods=["patch"])
    def generate(self, request, pk):
        scene = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        operation = queue_scene_job(
            scene, rewrite_scene_task, serializer.validated_data["text"],
        )
        return Response(operation, status=status.HTTP_202_ACCEPTED)

    @swagger_auto_schema(
        operation_description="Updates a scene image, or creates one when scene_image is omitted. "
        "Upload files using multipart/form-data. Audio-only updates also accept JSON.",
        method="POST",
        auto_schema=SceneImageUploadSchema,
        request_body=ChangeSceneImageSerializer,
        query_serializer=SceneImageQuerySerializer,
        responses={
            status.HTTP_200_OK: openapi.Response(
                "Scene image saved",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={"Message": openapi.Schema(type=openapi.TYPE_STRING)},
                ),
            ),
        },
    )
    @action(detail=True, methods=["POST"])
    def change_image_scene(self, request, pk):
        scene = self.get_object()
        query_serializer = SceneImageQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        scene_image_id = query_serializer.validated_data.get("scene_image")
        scene_image = None
        if scene_image_id is not None:
            scene_image = get_object_or_404(SceneImage, pk=scene_image_id, scene=scene)

        serializer = self.get_serializer(
            data=request.data,
            context={**self.get_serializer_context(), "has_scene_image": scene_image is not None},
        )
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        with editable_video(scene.video_id):
            image = validated_data.get("image")
            if scene_image:
                if image:
                    scene_image.file = image
                scene_image.with_audio = validated_data["with_audio"]
                scene_image.save()
            else:
                SceneImage.objects.create(
                    scene=scene,
                    file=image,
                    with_audio=validated_data["with_audio"],
                )

        return Response(
            {"Message": "Image Scene was added successfully"},
            status=status.HTTP_200_OK,
        )

    @swagger_auto_schema(
        operation_description="This api changes the image of the scene or it creates "
        "a new one if it doesnt exist",
        method="POST",
        request_body=GenerateSceneImageSerializer,
    )
    @action(detail=True, methods=["POST"])
    def generate_image_scene(self, request, pk):
        scene = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        operation = queue_scene_job(
            scene, generate_scene_image_task, serializer.validated_data["image_description"],
        )
        return Response(operation, status=status.HTTP_202_ACCEPTED)

    @swagger_auto_schema(query_serializer=SceneJobQuerySerializer, responses={200: "Background scene job status and result"})
    @action(detail=True, methods=["GET"])
    def operation(self, request, pk=None):
        scene = self.get_object()
        query = SceneJobQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        operation = scene_job_result(scene, query.validated_data["job"])
        return Response(operation, headers={"Cache-Control": "private, no-store"})

    def destroy(self, request, pk):
        obj = self.get_object()
        with editable_video(obj.video_id):
            obj.delete()

        return Response(dict(message="Scene deleted successfully"), status=204)
