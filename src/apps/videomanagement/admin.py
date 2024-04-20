from django.contrib import admin
from .models import *
from django.contrib import admin
from .utils.video_utils import make_video


class VideoAdmin(admin.ModelAdmin):
    @admin.action
    def render_video(self, _, queryset):
        if len(queryset) > 1:
            return "You can only render 1 video per time"

        make_video(queryset.first())

        return "Success"
    # Register the action with the model
    actions = ['render_video']


# Register your models here.
admin.site.register(Videos, VideoAdmin)
admin.site.register(TemplatePrompts)
admin.site.register(SceneImage)
admin.site.register(Scene)
admin.site.register(UserPrompt)
admin.site.register(Music)
admin.site.register(VoiceModels)
admin.site.register(Intro)
admin.site.register(Outro)
admin.site.register(Backgrounds)
admin.site.register(Avatars)
