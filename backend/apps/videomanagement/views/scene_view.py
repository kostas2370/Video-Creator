from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ..models import Scene, SceneImage, Video
from ..serializers import SceneSerializer
from ..services.SceneServices import generate_scene, update_scene
from ..swagger_serializers import SceneUpdateSerializer
from ..utils.visual_utils import generate_new_image
from ..permissions import IsOwnerPermission, SceneGenerationLimitPermission

scene_id = openapi.Parameter(
    "scene_id",
    openapi.IN_QUERY,
    description="Id of the scene you want to change.",
    type=openapi.TYPE_NUMBER,
)

scene_image_id = openapi.Parameter(
    "scene_image",
    openapi.IN_QUERY,
    description="Id of the scene Image you want to change.",
    type=openapi.TYPE_NUMBER,
)


class SceneView(viewsets.GenericViewSet):
    serializer_class = SceneSerializer
    queryset = Scene.objects.all()
    permission_classes = [
        IsAuthenticated,
        IsOwnerPermission,
        SceneGenerationLimitPermission,
    ]

    @swagger_auto_schema(
        request_body=SceneUpdateSerializer,
        operation_description="This API updates the text of a scene and regenerates their dialogue "
        "with the new text",
    )
    def partial_update(self, request, pk=None):
        instance = self.get_object()

        updated_scene = update_scene(request.data.get("text"), instance)

        request.user.generation_limit_for_ai -= 0.01
        request.user.save()

        return Response({"text": updated_scene}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=SceneUpdateSerializer,
        operation_description="This API sends the dialogue into gpt and changes it depending on the "
        "prompt user sends of th of a scene and regenerates their dialogue "
        "with the new text",
    )
    @action(detail=True, methods=["patch"])
    def generate(self, request, pk):
        text = request.data.get("text").strip()
        scene = self.get_object()

        generated_scene = generate_scene(text, scene)
        request.user.generation_limit_for_ai -= 0.03
        request.user.save()
        return Response({"text": generated_scene}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="This api changes the image of the scene or it creates "
        "a new one if it doesnt exists",
        method="POST",
        manual_parameters=[scene_id],
    )
    @action(detail=True, methods=["POST"])
    def change_image_scene(self, request, pk):
        scene_image = request.GET.get("scene_image")
        image = request.FILES.get("image")
        with_audio = request.data.get("with_audio", False)

        if scene_image:
            img = SceneImage.objects.get(id=scene_image)
            if image:
                img.file = image

            img.with_audio = with_audio
            img.save()

        else:
            if not image:
                return Response({"message": "You must add an image !"}, status=400)
            SceneImage.objects.create(scene_id=pk, file=image, with_audio=with_audio)

        return Response({"Message": "Image Scene was added successfully"})

    @swagger_auto_schema(
        operation_description="This api changes the image of the scene or it creates "
        "a new one if it doesnt exists",
        method="POST",
        manual_parameters=[scene_id],
    )
    @action(detail=True, methods=["POST"])
    def generate_image_scene(self, request, pk):
        img = SceneImage.objects.filter(scene_id=pk).first()
        image_description = request.data.get("image_description")
        video = Video.objects.filter(prompt__scene__sceneimage=img).distinct().first()

        if not image_description:
            return Response(
                {"message": "Image description can not be blank"}, status=400
            )

        if not img:
            img = SceneImage.objects.create(prompt=image_description, scene_id=pk)

        img.prompt = image_description
        img.save()
        generate_new_image(img, video)

        request.user.generation_limit_for_ai -= 0.08
        request.user.save()

        return Response({"Message": "Image Scene was added successfully"})

    def destroy(self, request, pk):
        obj = self.get_object()
        obj.delete()

        return Response(dict(message="Scene deleted successfully"), status=204)
