from django.db import models
from django.contrib.auth import get_user_model

TEMPLATE_CHOICES = (("EDUCATIONAL", "Educational"), ("GAMING", "Gaming"), ("ADVERTISEMENT", "Advertisement"),
                    ("STORY", "Story"), ("OTHER", "Other"))

MODEL_TYPE_CHOICES = (("API", "Api"), ("LOCAL", "Local"))


class AbstractModel(models.Model):
    created_by = models.ForeignKey(get_user_model(), on_delete = models.CASCADE, blank = True, null = True)
    creation_date = models.DateField(auto_now = True)
    update_date = models.DateField(auto_now = True)

    class Meta:
        abstract = True


class TemplatePrompts(AbstractModel):
    title = models.CharField(max_length = 20, blank = False)
    category = models.CharField(choices = TEMPLATE_CHOICES, max_length = 20, null = True)
    format = models.TextField(blank = True)

    def __str__(self):
        return self.title


class Music(AbstractModel):
    name = models.CharField(max_length = 140, blank = False)
    file = models.FileField(upload_to = "media/music", blank = False)
    category = models.CharField(choices = TEMPLATE_CHOICES, max_length = 20, null = True)

    def __str__(self):
        return self.name


class UserPrompt(models.Model):
    template = models.ForeignKey(TemplatePrompts, on_delete = models.CASCADE, blank = True)
    prompt = models.TextField(blank = False)
    music = models.ForeignKey(Music, blank = True, null = True, on_delete = models.SET_NULL)

    def __str__(self):
        return f'{self.template.title} {self.id}'


class Speech(models.Model):
    prompt = models.ForeignKey(UserPrompt, on_delete = models.CASCADE)
    file = models.FileField(upload_to = "media/speech")
    text = models.TextField()


    def __str__(self):
        return str(self.id)


class SpeechImage(models.Model):
    scene = models.ForeignKey(Speech, on_delete = models.CASCADE)
    file = models.ImageField(upload_to = "media/images")


class Videos(AbstractModel):
    title = models.CharField(max_length = 50, blank = False)
    description = models.CharField(max_length = 300, blank = True)
    url = models.URLField(blank = True)
    gpt_answer = models.TextField(blank = True, null = True)
    prompt = models.ForeignKey(UserPrompt, related_name = 'video_prompt', on_delete = models.CASCADE)
    output = models.FileField(upload_to = "media/output")

    def __str__(self):
        return self.title + str(self.id)


class VoiceModels(AbstractModel):
    gender = models.CharField(max_length = 3)
    type = models.CharField(max_length = 10, choices = MODEL_TYPE_CHOICES)
    sample = models.FileField(upload_to = "media/model_samples")
    path = models.CharField(max_length = 255, blank = False)

    def __str__(self):
        return self.path


class Intro(AbstractModel):
    category = models.CharField(max_length = 30, choices = TEMPLATE_CHOICES)
    name = models.CharField(max_length = 100)
    file = models.FileField(upload_to = "media/other/intros")


class Outro(AbstractModel):
    category = models.CharField(max_length = 30, choices = TEMPLATE_CHOICES)
    name = models.CharField(max_length = 100)
    file = models.FileField(upload_to = "media/other/outros")


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

    def __str__(self):
        return self.name


class Avatars(AbstractModel):
    gender = models.CharField(max_length = 10)
    file = models.FileField(upload_to = "media/other/avatars")
    voice = models.ForeignKey(VoiceModels, null = True, on_delete = models.SET_NULL, default = 1)


