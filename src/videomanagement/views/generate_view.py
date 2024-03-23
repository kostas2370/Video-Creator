from rest_framework.response import Response
from slugify import slugify
from rest_framework import viewsets

from drf_yasg.utils import swagger_auto_schema


from django.conf import settings

from ..utils.download_utils import  create_image_scenes, download_music

from ..utils.prompt_utils import format_prompt, format_prompt_for_official_gpt
from ..utils.gpt_utils import get_reply, get_reply_from_official_api
from ..utils.audio_utils import make_scenes_speech
from ..utils.file_utils import generate_directory
from ..serializers import TemplatePromptsSerializer
from ..models import TemplatePrompts, Videos, VoiceModels, UserPrompt, Avatars, Backgrounds

from ..defaults import default_format

from ..swagger_serializers import GenerateSerializer


class GenerateView(viewsets.ViewSet):
    serializer_class = TemplatePromptsSerializer
    queryset = TemplatePrompts.objects.all()

    @swagger_auto_schema(request_body = GenerateSerializer,
                         operation_description = "This API generates the scenes , the prompt and scene images !")
    def create(self, request, *args, **kwargs):
        template_id = request.data.get('template_id', 2)
        voice_id = request.data.get('voice_id', None)
        message = request.data.get('message')
        gpt_model = request.data.get('gpt_model', 'gpt-4')
        images = request.data.get('images', False)
        avatar_selection = request.data.get('avatar_selection', 'no_avatar')
        style = request.data.get("style", "natural")
        music = request.data.get("music")
        target_audience = request.data.get('target_audience')
        background = request.data.get('background')

        if background == "random":
            background = Backgrounds.objects.all()
            background = background.first() if background else None

        avatar_selection = int(avatar_selection) if avatar_selection.isnumeric() else "no_avatar"

        template = TemplatePrompts.get_template(template_id)

        if template:
            category = template.category
            template_format = template.format

        else:
            template_format = default_format
            category = template_id if len(template_id) > 0 and not template_id.isnumeric() else ""
            template = None

        if settings.GPT_OFFICIAL:
            prompt = format_prompt_for_official_gpt(template_format = template_format, template_category = category,
                                                    userprompt = message, target_audience = target_audience)

            x = get_reply_from_official_api(message)
            message = prompt[0]+prompt[1]

        else:
            prompt = format_prompt(template_format = template_format, template_category = category,
                                   userprompt = message, target_audience = target_audience)

            x = get_reply(prompt, gpt_model = gpt_model)

        userprompt = UserPrompt.objects.create(template = template, prompt = F'{message}')
        userprompt.save()

        dir_name = generate_directory(rf'media\videos\{slugify(x["title"])}')

        vid = Videos.objects.create(title = x['title'],
                                    prompt = userprompt,
                                    dir_name = dir_name,
                                    gpt_answer = x,
                                    background = background)

        if avatar_selection != "no_avatar":
            selected_avatar = Avatars.select_avatar(selected = avatar_selection)
            voice_model = selected_avatar.voice
            vid.avatar = selected_avatar

        else:
            voice_model = VoiceModels.objects.get(id = voice_id) if voice_id else VoiceModels.select_voice()

        vid.voice_model = voice_model
        vid.save()

        make_scenes_speech(vid)

        if music:
            vid.music = download_music(music)

        if images:
            vid.mode = images
            create_image_scenes(vid, mode = images, style = style)

        vid.status = "GENERATION"
        vid.save()
        return Response({"message": "The video has been generated successfully"})
