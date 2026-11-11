from django.contrib import admin

from .models import (
    Avatar,
    Icon,
    Intro,
    Music,
    MusicCatalogTrack,
    Outro,
    Scene,
    SceneImage,
    TemplatePrompt,
    UserPrompt,
    Video,
    VoiceModel,
)
from .services.videos.jobs import queue_render


@admin.register(MusicCatalogTrack)
class MusicCatalogTrackAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "approved")
    list_filter = ("category", "approved")
    search_fields = ("title", "source_url", "attribution")
    readonly_fields = ("source_id", "metadata")


class VideoAdmin(admin.ModelAdmin):
    @admin.action
    def render_video(self, _, queryset):
        if len(queryset) > 1:
            return "You can only render 1 video per time"

        queue_render(queryset.first())

        return "Queued"

    # Register the action with the model
    actions = ["render_video"]


# Register your models here.
admin.site.register(Video, VideoAdmin)
admin.site.register(TemplatePrompt)
admin.site.register(SceneImage)
admin.site.register(Scene)
admin.site.register(UserPrompt)
admin.site.register(Music)
admin.site.register(VoiceModel)
admin.site.register(Intro)
admin.site.register(Outro)
admin.site.register(Avatar)


@admin.register(Icon)
class IconAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "collection", "created_by", "enabled")
    search_fields = ("key", "name", "description")
    list_filter = ("collection", "enabled")
