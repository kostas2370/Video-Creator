from django.contrib import admin

from .models import (
    Avatar,
    Icon,
    Intro,
    MediaAsset,
    Music,
    Outro,
    Scene,
    SceneImage,
    TemplatePrompt,
    UserPrompt,
    Video,
    VoiceModel,
)
from .services.videos.jobs import queue_render


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "is_shared", "catalog_approved", "created_by")
    list_filter = ("is_shared", "catalog_approved", "kind")
    search_fields = ("title", "source_url", "attribution")
    readonly_fields = ("catalog_source_id", "catalog_metadata", "checksum")


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
