from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(Videos)
admin.site.register(TemplatePrompts)
admin.site.register(SpeechImage)
admin.site.register(Speech)
admin.site.register(UserPrompt)
admin.site.register(Music)
admin.site.register(VoiceModels)
admin.site.register(Intro)
admin.site.register(Outro)
admin.site.register(Backgrounds)
admin.site.register(Avatars)