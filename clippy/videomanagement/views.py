from rest_framework.response import Response
from slugify import slugify
from rest_framework.permissions import AllowAny
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes, action
from django.db.models import Q
from rest_framework.pagination import PageNumberPagination
from rest_framework import status
import urllib.request


from .utils.video_utils import make_video
from .utils.download_utils import download_playlist, create_image_scenes, download_video
from .utils.prompt_utils import format_prompt, format_update_form
from .utils.gpt_utils import get_reply, get_update_sentence
from .utils.audio_utils import make_scenes_speech, update_scene
from .utils.file_utils import generate_directory, select_avatar, select_voice
from .serializers import TemplatePromptsSerializer, MusicSerializer, VideoSerializer, AvatarNestedSerializer, \
    SceneSerializer, VoiceModelSerializer, AvatarSerializer, VideoNestedSerializer, SceneImageSerializer
from .models import TemplatePrompts, Music, Videos, VoiceModels, UserPrompt, Avatars, Scene, SceneImage, Backgrounds, \
    Intro, Outro


class SceneView(viewsets.ModelViewSet):
    serializer_class = SceneSerializer
    queryset = Scene.objects.all()
    permission_classes = [AllowAny]

    def partial_update(self, request, pk=None):
        instance = self.get_object()
        if not instance:
            return Response(status = status.HTTP_404_NOT_FOUND)

        new_text = request.data.get('text', None)

        instance.text = new_text if new_text else instance.text
        update_scene(instance)

        return Response({"message": "Your scene updated Succcessfuly", "scene": SceneSerializer(instance).data},
                        status = status.HTTP_200_OK)

    @action(detail = True, methods = ['patch'])
    def generate(self, request, pk):
        text = request.data.get("text").strip()
        scene = self.get_object()

        if text == scene.text.strip():
            return Response({"message": "Your scene updated Succcessfuly"}, status = status.HTTP_200_OK)

        if text:
            scene.text = get_update_sentence(format_update_form(scene.text, text))

        update_scene(scene)
        return Response({"message": "Your scene updated Succcessfuly"},
                        status = status.HTTP_200_OK)


class SceneImageView(viewsets.ModelViewSet):
    queryset = SceneImage.objects.all()
    serializer_class = SceneImageSerializer
    permission_classes = [AllowAny]


class TemplatePromptView(viewsets.ModelViewSet):
    serializer_class = TemplatePromptsSerializer
    queryset = TemplatePrompts.objects.all()
    permission_classes = [AllowAny]


class MusicView(viewsets.ModelViewSet):
    serializer_class = MusicSerializer
    queryset = Music.objects.all()
    permission_classes = [AllowAny]


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 1000


class VideoView(viewsets.ModelViewSet):
    serializer_class = VideoSerializer
    queryset = Videos.objects.filter(~Q(gpt_answer=None)).order_by("-id")
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.action == "retrieve":
            return VideoNestedSerializer

        return VideoSerializer


class VoiceView(viewsets.ModelViewSet):
    serializer_class = VoiceModelSerializer
    queryset = VoiceModels.objects.all()
    permission_classes = [AllowAny]


class AvatarView(viewsets.ModelViewSet):
    serializer_class = AvatarSerializer
    queryset = Avatars.objects.all()
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == "list":
            return AvatarNestedSerializer

        return AvatarSerializer


class GenerateView(viewsets.ModelViewSet):
    serializer_class = TemplatePromptsSerializer
    queryset = TemplatePrompts.objects.all()
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        template_id = request.data.get('template_id', 2)
        voice_id = request.data.get('voice_id', None)
        title = request.data.get('title')
        prompt = request.data.get('message')
        gpt_model = request.data.get('gpt_model', 'gpt-3.5-turbo')
        images = request.data.get('images', False)
        avatar_selection = request.data.get('avatar_selection', 'no_avatar')
        style = request.data.get("style", "natural")

        if avatar_selection != 'random' and avatar_selection !="no_avatar":
            avatar_selection = int(avatar_selection)

        target_audience = request.data.get('target_audience')

        template = TemplatePrompts.objects.get(id = template_id)

        message = format_prompt(template, userprompt = prompt, title = title, target_audience = target_audience)

        userprompt = UserPrompt.objects.create(template = template, prompt = message)
        userprompt.save()

        vid = Videos.objects.create(title = title, prompt = userprompt)

        x = get_reply(message, gpt_model = gpt_model)
        dir_name = generate_directory(rf'media\media\videos\{slugify(x["title"])}')
        vid.dir_name, vid.gpt_answer = dir_name, x

        if type(avatar_selection) is int:
            selected_avatar = select_avatar(selected = avatar_selection)
            voice_model = selected_avatar.voice
            vid.avatar = selected_avatar

        elif avatar_selection == "random":
            selected_avatar = select_avatar()
            voice_model = selected_avatar.voice
            vid.avatar = selected_avatar

        elif voice_id is not None:
            voice_model = VoiceModels.objects.get(id = voice_id)

        else:
            voice_model = select_voice()

        vid.voice_model = voice_model

        vid.save()
        make_scenes_speech(vid)

        if images:

            create_image_scenes(vid, mode = images, style = style)

        vid.status = "GENERATION"
        vid.save()
        return Response({"message": "The video has been made successfully"})


@api_view(['POST'])
@permission_classes([AllowAny])
def download_playlist(request):
    link = request.data['link']
    download_playlist(link, category = request.data.get('category'))
    return Response({'Message': 'Successful'})


@api_view(['POST'])
@permission_classes([AllowAny])
def render_video(request):
    vid = Videos.objects.get(id = request.GET.get('video_id'))
    vid.status = "RENDERING"
    vid.save()
    result = make_video(vid, avatar = True if vid.avatar else False)
    return Response({"message": "The video has been made succfully", "result": VideoSerializer(result).data})


@api_view(['POST'])
@permission_classes([AllowAny])
def change_image_scene(request):
    scene = request.GET.get("scene_id")
    scene_image = request.GET.get("scene_image")
    image = request.FILES.get("image")

    if not image:
        return Response({"message": "You must add a photo!"}, status = status.HTTP_400_BAD_REQUEST)

    if scene_image:
        img = SceneImage.objects.get(id = scene_image)
        img.file = image
        img.save()

    else:
        SceneImage.objects.create(scene_id = scene, file = image)

    return Response({"Message": "Image Scene was added successfully"})


@api_view(['GET'])
@permission_classes([AllowAny])
def setup(request):

    if Intro.objects.filter(name="basicintro").count()==0:
        intro = download_video("https://www.youtube.com/watch?v=fQaEv_odk0w", "media/other/intros/")
        Intro.objects.create(category = "OTHER", name = "basicintro", file = intro)

    if Outro.objects.filter(name="basicoutro").count()==0:
        outro = download_video("https://www.youtube.com/watch?v=YqB62GjZqC0", "media/other/outros/")
        Outro.objects.create(category = "OTHER", name = "basicoutro", file = outro)

    if Backgrounds.objects.filter(name="basicbackground").count() == 0 :

        background_url = "https://i.ibb.co/SPz879q/back.jpg"
        urllib.request.urlretrieve(background_url, "media/other/backgrounds/back.png")

        Backgrounds.objects.create(category = "OTHER",
                                   name= "basicbackground",
                                   file = "media/other/backgrounds/back.png",
                                   color = "0,163,232",
                                   image_pos_top=65,
                                   image_pos_left = 355,
                                   avatar_pos_top = 0,
                                   avatar_pos_left = 0,
                                   through = 6)

    return Response({"message" : "setup ok"})

