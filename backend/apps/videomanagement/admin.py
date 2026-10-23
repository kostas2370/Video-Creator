from django.contrib import admin
from django.utils import timezone

from .models import (
    Avatar,
    Intro,
    Music,
    NewsUpdate,
    Outro,
    Scene,
    SceneImage,
    TemplatePrompt,
    UserPrompt,
    Video,
    VoiceModel,
)
from .tasks import render_video_task


@admin.register(NewsUpdate)
class NewsUpdateAdmin(admin.ModelAdmin):
    list_display = ["title", "status", "published_at", "updated_at"]
    list_filter = ["status", "published_at"]
    search_fields = ["title", "content"]
    date_hierarchy = "published_at"
    readonly_fields = ["created_at", "updated_at"]
    fields = ["title", "content", "status", "published_at", "created_at", "updated_at"]
    actions = ["publish_now", "move_to_draft"]

    @admin.action(description="Publish selected updates now")
    def publish_now(self, request, queryset):
        now = timezone.now()
        count = queryset.update(
            status=NewsUpdate.Status.PUBLISHED, published_at=now, updated_at=now
        )
        self.message_user(request, f"Published {count} news updates.")

    @admin.action(description="Move selected updates to draft")
    def move_to_draft(self, request, queryset):
        count = queryset.update(status=NewsUpdate.Status.DRAFT, updated_at=timezone.now())
        self.message_user(request, f"Moved {count} news updates to draft.")


class VideoAdmin(admin.ModelAdmin):
    @admin.action
    def render_video(self, _, queryset):
        if len(queryset) > 1:
            return "You can only render 1 video per time"

        render_video_task.delay(video_id=queryset.first().pk)

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
