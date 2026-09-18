from django.contrib import admin

from .models import ApiKeys
from .serializers import KEY_FIELDS


@admin.register(ApiKeys)
class ApiKeysAdmin(admin.ModelAdmin):
    list_display = ("user", "providers_set", "updated_at")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("user",)

    @admin.display(description="providers set")
    def providers_set(self, obj):
        filled = [field for field in KEY_FIELDS if getattr(obj, field, "")]
        return ", ".join(field.replace("_", " ") for field in filled) or "—"
