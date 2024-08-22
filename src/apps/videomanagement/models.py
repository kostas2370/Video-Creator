from __future__ import annotations
from django.db import models
from django.contrib.auth import get_user_model
from random import randint
from typing import Union
from django_resized import ResizedImageField

TEMPLATE_CHOICES = (("EDUCATIONAL", "Educational"), ("GAMING", "Gaming"), ("ADVERTISEMENT", "Advertisement"),
                    ("STORY", "Story"), ("OTHER", "Other"))

MODEL_TYPE_CHOICES = (("API", "Api"), ("LOCAL", "Local"), ("PYTTSX3", "Pyttsx3"))

VIDEO_STATUS = (("GENERATION", "GENERATION"), ("READY", "READY"), ("RENDERING", "RENDERING"), ("COMPLETED", "COMPLETED")
                , ("FAILED", "FAILED"))


IMAGE_MODE = (("DALL-E", "DALL-E"), ("WEB", "WEB"))

VIDEO_TYPE = (("AI", "AI"), ("TWITCH", "TWITCH"))


class AbstractModel(models.Model):
    created_by = models.ForeignKey(get_user_model(), on_delete = models.CASCADE, blank = True, null = True)
    objects = models.Manager()

    class Meta:
        abstract = True


class TemplatePrompts(AbstractModel):
    title = models.CharField(max_length = 20, blank = False)
    category = models.CharField(choices = TEMPLATE_CHOICES, max_length = 20, null = True)
    format = models.TextField(blank = True)
    is_sentenced = models.BooleanField(default = False)
    objects = models.Manager()

    def __str__(self):
        return self.title

    @staticmethod
    def get_template(template_select: str) -> Union[TemplatePrompts, None]:
        if template_select.isnumeric():
            template = TemplatePrompts.objects.filter(id = template_select)

        elif len(template_select) > 0:
            template = TemplatePrompts.objects.filter(category = template_select.upper())

        else:
            template = None

        return template.first() if template and template.count() > 0 else None


class Music(AbstractModel):
    name = models.CharField(max_length = 140, blank = False)
    file = models.FileField(upload_to = "media/music", blank = False)
    category = models.CharField(choices = TEMPLATE_CHOICES, max_length = 20, null = True)
    objects = models.Manager()

    def __str__(self):
        return self.name

    @staticmethod
    def select_music(category: str = None) -> Union[Music, None]:
        if category is None:
            music = Music.objects.all()

        else:
            music = Music.objects.filter(category = category)

        if music.count() > 0:
            return music[randint(0, music.count()-1)]

        return None


class UserPrompt(models.Model):
    template = models.ForeignKey(TemplatePrompts, on_delete = models.CASCADE, blank = True, null = True)
    prompt = models.TextField(blank = False)
    objects = models.Manager()

    def __str__(self):
        return f'{self.id}'


class Scene(models.Model):
    prompt = models.ForeignKey(UserPrompt, on_delete = models.CASCADE)
    file = models.FileField(upload_to = "media/speech", blank = True, null = True, max_length = 2000)
    text = models.TextField()
    is_last = models.BooleanField(default = True)
    objects = models.Manager()

    def __str__(self):
        return str(self.id)


class SceneImage(models.Model):
    scene = models.ForeignKey(Scene, on_delete = models.CASCADE)
    file = models.FileField(upload_to = "media/images", null = True, blank = True, max_length = 2000)
    prompt = models.TextField(default = "", blank = True, null = True)
    with_audio = models.BooleanField(default = False)
    objects = models.Manager()


class VoiceModels(AbstractModel):
    name = models.CharField(max_length = 200, blank = True)
    provider = models.CharField(max_length = 100, blank = True)
    type = models.CharField(max_length = 10, choices = MODEL_TYPE_CHOICES)
    sample = models.URLField(blank = True, null=True, max_length = 1000)
    path = models.CharField(max_length = 255, blank = False)
    objects = models.Manager()

    def __str__(self):
        return self.name

    @staticmethod
    def select_voice() -> VoiceModels:
        voice = VoiceModels.objects.all()
        return voice[randint(0, voice.count()-1)]


class Avatars(AbstractModel):
    name = models.CharField(max_length = 100, default = "Natasha")
    gender = models.CharField(max_length = 10)
    file = ResizedImageField(size=[256, 256], quality=75, upload_to = "media/other/avatars", force_format='jpeg')
    voice = models.ForeignKey(VoiceModels, null = True, on_delete = models.SET_NULL, db_constraint=False)
    objects = models.Manager()

    def __str__(self):
        return self.name

    @staticmethod
    def select_avatar(selected: str = 'random', voice_model: VoiceModels = None) -> Union[Avatars, None]:
        if selected == 'random':
            if voice_model is None:
                avatars = Avatars.objects.all()
            else:
                avatars = Avatars.objects.filter(voice = voice_model)

            return avatars[randint(0, avatars.count()-1)]

        if isinstance(selected, int):
            items = Avatars.objects.filter(id = selected)
            if items.count() == 1:
                return items.first()

        return None


class Backgrounds(AbstractModel):
    category = models.CharField(max_length = 30, choices = TEMPLATE_CHOICES)
    name = models.CharField(max_length = 100)
    file = models.FileField(upload_to = "media/other/backgrounds")
    color = models.CharField(max_length = 30)
    image_pos_top = models.IntegerField()
    image_pos_left = models.IntegerField()
    avatar_pos_top = models.IntegerField()
    avatar_pos_left = models.IntegerField()
    through = models.IntegerField(default = 6)
    objects = models.Manager()

    def __str__(self):
        return self.name

    @staticmethod
    def select_background(category: str = None) -> Backgrounds:
        if category is not None:
            back = Backgrounds.objects.filter(category = category)
        else:

            back = Backgrounds.objects.all()

        return back[randint(0, back.count()-1)]


class Intro(AbstractModel):
    category = models.CharField(max_length = 30, choices = TEMPLATE_CHOICES)
    name = models.CharField(max_length = 100)
    file = models.FileField(upload_to = "media/other/intros")
    objects = models.Manager()


class Outro(AbstractModel):
    category = models.CharField(max_length = 30, choices = TEMPLATE_CHOICES)
    name = models.CharField(max_length = 100)
    file = models.FileField(upload_to = "media/other/outros")
    objects = models.Manager()


class Videos(AbstractModel):
    title = models.CharField(max_length = 50, blank = False)
    url = models.URLField(blank = True)
    gpt_answer = models.TextField(blank = True, null = True)
    prompt = models.ForeignKey(UserPrompt, related_name = 'video_prompt', on_delete = models.CASCADE)
    output = models.FileField(upload_to = "media/output", blank = True, null=True, max_length = 2000)
    dir_name = models.TextField(default = "")
    voice_model = models.ForeignKey(VoiceModels, on_delete = models.SET_NULL, null = True, default = 1,
                                    db_constraint=False)
    avatar = models.ForeignKey(Avatars, on_delete = models.SET_NULL, null = True, default = None, blank = True,
                               db_constraint=False)
    status = models.CharField(max_length = 20, choices = VIDEO_STATUS, default = "RENDERING")
    music = models.ForeignKey(Music, blank = True, null = True, on_delete = models.SET_NULL)
    background = models.ForeignKey(Backgrounds, blank = True, null = True, on_delete = models.SET_NULL)
    intro = models.ForeignKey(Intro, blank = True, null = True, on_delete = models.SET_NULL)
    outro = models.ForeignKey(Outro, blank = True, null = True, on_delete = models.SET_NULL)
    subtitles = models.BooleanField(default = False)
    video_type = models.CharField(max_length = 20, default = "AI", choices = VIDEO_TYPE)
    mode = models.CharField(max_length = 30, choices=IMAGE_MODE, default = "WEB" , null = True)

    objects = models.Manager()

    def __str__(self):
        return f"{self.title}"
