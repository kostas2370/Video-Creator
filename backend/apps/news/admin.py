from django.contrib import admin
from django.utils import timezone

from .models import NewsUpdate


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
