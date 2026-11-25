from django.contrib import admin

from apps.usermanagement.admin import SuperuserAdminMixin

from .models import ApiKeys
from .serializers import KEY_FIELDS


@admin.register(ApiKeys)
class ApiKeysAdmin(SuperuserAdminMixin, admin.ModelAdmin):
    list_display = ("user", "updated_at")
    search_fields = ("user__username", "user__email")
    fields = ("user", "created_at", "updated_at")
    readonly_fields = fields
    list_select_related = ("user",)

    def get_queryset(self, request):
        return super().get_queryset(request).defer(*KEY_FIELDS)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
