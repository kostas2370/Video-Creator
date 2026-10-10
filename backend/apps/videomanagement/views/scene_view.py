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
from ..serializers import SceneSerializer
from ..services.SceneServices import generate_scene, update_scene
from ..services.editing import update_scene_transition, update_scene_timing
from ..request_serializers import (
    ChangeSceneImageSerializer,
    GenerateSceneImageSerializer,
    SceneImageQuerySerializer,
    SceneUpdateSerializer,
    SceneTransitionSerializer,
    SceneTimingSerializer,
)
from ..utils.scenes import generate_new_image
from ..utils.cost_utils import reserve_scene_credit
from ..permissions import IsOwnerPermission, SceneGenerationLimitPermission


class SceneView(viewsets.GenericViewSet):
    serializer_class = SceneSerializer
    queryset = Scene.objects.all()
    permission_classes = [
        IsAuthenticated,
        IsOwnerPermission,
        SceneGenerationLimitPermission,
    ]

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

        with reserve_scene_credit(
            request.user, 0.01, SceneGenerationLimitPermission.required_limit
        ):
            updated_scene = update_scene(serializer.validated_data["text"], instance)

        return Response(
            {"text": updated_scene, "narration_status": SceneSerializer(instance).data["narration_status"]},
            status=status.HTTP_200_OK,
        )

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
        text = serializer.validated_data["text"]

        with reserve_scene_credit(
            request.user, 0.03, SceneGenerationLimitPermission.required_limit
        ):
            generated_scene = generate_scene(text, scene)
        return Response({"text": generated_scene}, status=status.HTTP_200_OK)

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
        img = scene.scene_images.first()
        image_description = serializer.validated_data["image_description"]
        video = scene.video

        with reserve_scene_credit(
            request.user, 0.08, SceneGenerationLimitPermission.required_limit
        ):
            if not img:
                img = SceneImage.objects.create(prompt=image_description, scene=scene)

            img.prompt = image_description
            img.save()
            generate_new_image(img, video)

        return Response({"Message": "Image Scene was added successfully"})

    def destroy(self, request, pk):
        obj = self.get_object()
        obj.delete()

        return Response(dict(message="Scene deleted successfully"), status=204)
