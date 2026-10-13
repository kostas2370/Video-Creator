from django.shortcuts import get_object_or_404
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ..models import Scene, SceneImage
from ..schema import SceneImageUploadSchema
from ..tasks import update_scene_task, rewrite_scene_task, generate_scene_image_task
from ..serializers.models import SceneSerializer
from ..services.scene_jobs import queue_scene_job, scene_job_result
from ..services.editing import editable_video
from ..serializers.requests import SceneJobQuerySerializer
from ..services.editing import update_scene_transition, update_scene_timing
from ..serializers.requests import (
    ChangeSceneImageSerializer,
    GenerateSceneImageSerializer,
    SceneImageQuerySerializer,
    SceneUpdateSerializer,
    SceneTransitionSerializer,
    SceneTimingSerializer,
)
from ..permissions import IsOwnerPermission, SceneGenerationLimitPermission


from ..serializers.audio import SceneAudioSerializer, VoiceoverUploadSerializer
from ..services.audio_editing import update_audio, save_voiceover, audio_waveform


class SceneView(viewsets.GenericViewSet):
    serializer_class = SceneSerializer
    queryset = Scene.objects.all()
    permission_classes = [
        IsAuthenticated,
        IsOwnerPermission,
        SceneGenerationLimitPermission,
    ]

    @swagger_auto_schema(request_body=SceneAudioSerializer)
    @action(detail=True, methods=["PATCH"], permission_classes=[IsAuthenticated, IsOwnerPermission])
    def audio(self, request, pk=None):
        scene = self.get_object()
        serializer = SceneAudioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(SceneSerializer(update_audio(scene, serializer.validated_data)).data)

    @action(detail=True, methods=["POST", "DELETE"], parser_classes=[MultiPartParser, FormParser],
            permission_classes=[IsAuthenticated, IsOwnerPermission])
    def voiceover(self, request, pk=None):
        scene = self.get_object()
        upload = None
        if request.method == "POST":
            serializer = VoiceoverUploadSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            upload = serializer.validated_data["file"]
        return Response(SceneSerializer(save_voiceover(scene, upload)).data)

    @action(detail=True, methods=["GET"], permission_classes=[IsAuthenticated, IsOwnerPermission])
    def waveform(self, request, pk=None):
        return Response(audio_waveform(self.get_object()), headers={"Cache-Control": "private, no-store"})

    @swagger_auto_schema(request_body=SceneTimingSerializer)
    @action(detail=True, methods=["PATCH"], permission_classes=[IsAuthenticated, IsOwnerPermission])
    def timing(self, request, pk=None):
        owned_scene = self.get_object()
        serializer = SceneTimingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scene = update_scene_timing(owned_scene, **serializer.validated_data)
        return Response(SceneSerializer(scene).data)

    @swagger_auto_schema(request_body=SceneTransitionSerializer)
    @action(detail=True, methods=["PATCH"], permission_classes=[IsAuthenticated, IsOwnerPermission])
    def transition(self, request, pk=None):
        owned_scene = self.get_object()
        serializer = SceneTransitionSerializer(data=request.data)
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
        serializer = SceneUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        operation = queue_scene_job(
            instance, request.user, update_scene_task, serializer.validated_data["text"], cost=0.01,
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
        serializer = SceneUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        operation = queue_scene_job(
            scene, request.user, rewrite_scene_task, serializer.validated_data["text"], cost=0.03,
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
    @action(
        detail=True,
        methods=["POST"],
        parser_classes=[MultiPartParser, FormParser, JSONParser],
    )
    def change_image_scene(self, request, pk):
        scene = self.get_object()
        query_serializer = SceneImageQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        scene_image_id = query_serializer.validated_data.get("scene_image")
        scene_image = None
        if scene_image_id is not None:
            scene_image = get_object_or_404(SceneImage, pk=scene_image_id, scene=scene)

        serializer = ChangeSceneImageSerializer(
            data=request.data,
            context={"has_scene_image": scene_image is not None},
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
        serializer = GenerateSceneImageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        operation = queue_scene_job(
            scene, request.user, generate_scene_image_task, serializer.validated_data["image_description"], cost=0.08,
        )
        return Response(operation, status=status.HTTP_202_ACCEPTED)

    @swagger_auto_schema(query_serializer=SceneJobQuerySerializer, responses={200: "Background scene job status and result"})
    @action(detail=True, methods=["GET"], permission_classes=[IsAuthenticated, IsOwnerPermission])
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
