from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import Scene, SceneImage
from ..serializers import SceneSerializer
from ..services.SceneServices import generate_scene, update_scene
from ..swagger_serializers import SceneUpdateSerializer

scene_id = openapi.Parameter('scene_id',
                             openapi.IN_QUERY,
                             description="Id of the scene you want to change.",
                             type=openapi.TYPE_NUMBER)

scene_image_id = openapi.Parameter('scene_image',
                                   openapi.IN_QUERY,
                                   description="Id of the scene Image you want to change.",
                                   type=openapi.TYPE_NUMBER)


class SceneView(viewsets.ModelViewSet):
    serializer_class = SceneSerializer
    queryset = Scene.objects.all()

    @swagger_auto_schema(request_body = SceneUpdateSerializer,
                         operation_description = "This API updates the text of a scene and regenerates their dialogue "
                                                 "with the new text")
    def partial_update(self, request, pk=None):
        instance = self.get_object()
        if not instance:
            return Response(status = status.HTTP_404_NOT_FOUND)

        updated_scene = update_scene(request.data.get("text"), instance)
        return Response({"text": updated_scene},
                        status = status.HTTP_200_OK)

    @swagger_auto_schema(request_body = SceneUpdateSerializer,
                         operation_description = "This API sends the dialogue into gpt and changes it depending on the "
                                                 "prompt user sends of th of a scene and regenerates their dialogue "
                                                 "with the new text")
    @action(detail = True, methods = ['patch'])
    def generate(self, request, pk):
        text = request.data.get("text").strip()
        scene = self.get_object()
        generated_scene = generate_scene(text, scene)
        return Response({"text": generated_scene},
                        status = status.HTTP_200_OK)

    @swagger_auto_schema(operation_description = "This api changes the image of the scene or it creates "
                                                 "a new one if it doesnt exists",
                         method = "POST",
                         manual_parameters = [scene_id])
    @action(detail = True, methods = ["POST"])
    def change_image_scene(self, request, pk):
        scene_image = request.GET.get("scene_image")
        image = request.FILES.get("image")

        if not image:
            return Response({"message": "You must add a photo!"}, status = status.HTTP_400_BAD_REQUEST)

        if scene_image:
            img = SceneImage.objects.get(id = scene_image)
            img.file = image
            img.save()

        else:
            SceneImage.objects.create(scene_id = pk, file = image)

        return Response({"Message": "Image Scene was added successfully"})
