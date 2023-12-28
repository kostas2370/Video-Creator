from django.db import models
from django.contrib.auth import get_user_model

TEMPLATE_CHOICES = (("EDUCATIONAL", "Educational"), ("GAMING", "Gaming"), ("ADVERTISEMENT", "Advertisement"),
                    ("STORY", "Story"), ("OTHER", "Other"))

MODEL_TYPE_CHOICES = (("API", "Api"), ("LOCAL", "Local"), ("PYTTSX3", "Pyttsx3"))

VIDEO_STATUS = (("RENDERING", "RENDERING"), ("GENERATED", "GENERATED"), ("COMPLETED", "COMPLETED"))


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


class Music(AbstractModel):
    name = models.CharField(max_length = 140, blank = False)
    file = models.FileField(upload_to = "media/music", blank = False)
    category = models.CharField(choices = TEMPLATE_CHOICES, max_length = 20, null = True)
    objects = models.Manager()

    def __str__(self):
        return self.name


class UserPrompt(models.Model):
    template = models.ForeignKey(TemplatePrompts, on_delete = models.CASCADE, blank = True, null = True)
    prompt = models.TextField(blank = False)
    objects = models.Manager()

    def __str__(self):
        return f'{self.id}'


class Scene(models.Model):
    prompt = models.ForeignKey(UserPrompt, on_delete = models.CASCADE)
    file = models.FileField(upload_to = "media/speech")
    text = models.TextField()
    is_last = models.BooleanField(default = True)
    objects = models.Manager()

    def __str__(self):
        return str(self.id)


class SceneImage(models.Model):
    scene = models.ForeignKey(Scene, on_delete = models.CASCADE)
    file = models.FileField(upload_to = "media/images")
    objects = models.Manager()


class VoiceModels(AbstractModel):
    gender = models.CharField(max_length = 3)
    type = models.CharField(max_length = 10, choices = MODEL_TYPE_CHOICES)
    sample = models.FileField(upload_to = "media/model_samples")
    path = models.CharField(max_length = 255, blank = False)
    objects = models.Manager()

    def __str__(self):
        return self.path


class Avatars(AbstractModel):
    name = models.CharField(max_length = 100, default = "Natasha")
    gender = models.CharField(max_length = 10)
    file = models.FileField(upload_to = "media/other/avatars")
    voice = models.ForeignKey(VoiceModels, null = True, on_delete = models.SET_NULL, db_constraint=False)
    objects = models.Manager()


class Videos(AbstractModel):
    title = models.CharField(max_length = 50, blank = False)
    url = models.URLField(blank = True)
    gpt_answer = models.TextField(blank = True, null = True)
    prompt = models.ForeignKey(UserPrompt, related_name = 'video_prompt', on_delete = models.CASCADE)
    output = models.FileField(upload_to = "media/output", blank = True, null=True)
    dir_name = models.TextField(default = "")
    voice_model = models.ForeignKey(VoiceModels, on_delete = models.SET_NULL, null = True, default = 1, db_constraint=False)
    avatar = models.ForeignKey(Avatars, on_delete = models.SET_NULL, null = True, default = None, blank = True, db_constraint=False)
    status = models.CharField(max_length = 20, choices = VIDEO_STATUS, default = "RENDERING")
    music = models.ForeignKey(Music, blank = True, null = True, on_delete = models.SET_NULL)

    objects = models.Manager()

    def __str__(self):
        return f"{self.title} { str(self.id)}"


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
