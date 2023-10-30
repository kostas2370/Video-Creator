from django.db import models
from django.contrib.auth import get_user_model

TEMPLATE_CHOICES = (("EDUCATIONAL", "Educational"), ("GAMING", "Gaming"), ("ADVERTISEMENT", "Advertisement"),
                    ("STORY", "Story"), ("OTHER", "Other"))

MODEL_TYPE_CHOICES = (("API", "Api"), ("LOCAL", "Local"))


class AbstractModel(models.Model):
    created_by = models.ForeignKey(get_user_model(),on_delete = models.CASCADE)
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
    name = models.CharField(max_length = 40, blank = False)
    file = models.FileField(upload_to = "media/music", blank = False)
    category = models.CharField(choices = TEMPLATE_CHOICES, max_length = 20, null = True)

    def __str__(self):
        return self.name


class UserPrompt(AbstractModel):
    template = models.ForeignKey(TemplatePrompts, on_delete = models.CASCADE, blank = True)
    prompt = models.TextField(blank = False)
    music = models.ForeignKey(Music, blank = True, null = True, on_delete = models.SET_NULL)

    def __str__(self):
        return f'{self.template.title} {self.created_by}'


class Speech(AbstractModel):
    prompt = models.ForeignKey(UserPrompt, on_delete = models.CASCADE)
    file = models.FileField(upload_to = "media/speech")


class Image(AbstractModel):
    prompt = models.ForeignKey(UserPrompt, on_delete = models.CASCADE)
    file = models.ImageField(upload_to = "media/images")


class Videos(AbstractModel):
    title = models.CharField(max_length = 50, blank = False)
    description = models.CharField(max_length = 300, blank = True)
    url = models.URLField(blank = True)
    prompt = models.ForeignKey(UserPrompt, on_delete = models.CASCADE)
    output = models.FileField(upload_to = "media/output")

    def __str__(self):
        return self.title


class VoiceModels(AbstractModel):
    gender = models.CharField(max_length = 3)
    type = models.CharField(max_length = 10, choices = MODEL_TYPE_CHOICES)
    sample = models.FileField(upload_to = "media/model_samples")
    path = models.CharField(max_length = 255, blank = False)

    def __str__(self):
        return self.path
