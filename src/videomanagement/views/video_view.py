from rest_framework.response import Response
from rest_framework import viewsets
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import action

import os
from drf_yasg.utils import swagger_auto_schema
from ..paginator import StandardResultsSetPagination
from ..utils.audio_utils import update_scene
from ..serializers import VideoSerializer, VideoNestedSerializer
from ..models import Videos, Avatars, Scene, SceneImage, Intro, Outro
from ..utils.download_utils import generate_new_image
from ..utils.video_utils import make_video


class VideoView(viewsets.ModelViewSet):
    serializer_class = VideoSerializer
    queryset = Videos.objects.filter(~Q(gpt_answer=None)).order_by("-id")
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.action == "retrieve":
            return VideoNestedSerializer

        return VideoSerializer

    @swagger_auto_schema(request_body = VideoSerializer,
                         operation_description = "This API updates the attributes of the video. If you add a new avatar"
                                                 " it will delete previous audio files and will regenerate them with "
                                                 "new audios")
    def partial_update(self, request, pk):
        avatar = request.data.get('avatar')
        intro = request.data.get('intro')
        outro = request.data.get('outro')

        video = self.get_object()

        if avatar and avatar == "no_value":
            video.avatar = None
            return Response("Avatar update")

        elif avatar and type(avatar) is str:
            selected_avatar = Avatars.objects.get(id = avatar)
            video.avatar = selected_avatar

            if video.voice_model != selected_avatar.voice:
                video.voice_model = selected_avatar.voice
                video.save()
                scenes = Scene.objects.filter(prompt = video.prompt)
                for scene in scenes:
                    update_scene(scene)

            return Response("Avatar update")

        intro = Intro.objects.get(id=intro) if intro is not None and intro != "no_value" else None \
            if intro == "no_value" else video.intro

        outro = Outro.objects.get(id=outro) if outro is not None and outro != "no_value" else None \
            if outro == "no_value" else video.outro

        video.intro = intro
        video.outro = outro
        video.save()
        return Response("Updated Success")

    @swagger_auto_schema(operation_description = "This api changes the image of the scene or it creates "
                                                 "a new one if it doesnt exists", method = "GET")
    @action(detail = True, methods = ["GET"])
    def video_regenerate(self, request, pk):

        if pk is None:

            return Response({'Message': "You must insert a video_id"}, status = status.HTTP_400_BAD_REQUEST)

        video = get_object_or_404(Videos, id = pk)
        with transaction.atomic():

            for scene in Scene.objects.filter(prompt = video.prompt):
                update_scene(scene)
                scenes_images = SceneImage.objects.filter(scene = scene)

                for scene_image in scenes_images:
                    generate_new_image(scene_image = scene_image, video = video)

            if video.avatar and os.path.exists(rf'{os.getcwd()}\{video.dir_name}\output_avatar.mp4'):
                os.remove(rf'{os.getcwd()}\{video.dir_name}\output_avatar.mp4')

        return Response({"Message": f"Video with id {pk} got regenerated successfully"}, status = status.HTTP_200_OK)

    @swagger_auto_schema(operation_description = "This api renders the video, you will have to put a query param in url"
                                                 " video_id with the video you wanna render", method = "GET")
    @action(detail = True, methods = ["GET"])
    def render_video(self, request, pk):
        vid = Videos.objects.get(id = pk)
        vid.status = "RENDERING"
        vid.save()
        result = make_video(vid)
        return Response({"message": "The video has been made successfully", "result": VideoSerializer(result).data})
