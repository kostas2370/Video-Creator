from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Login, User


class SuperuserAdminMixin:
    def has_module_permission(self, request):
        return request.user.is_superuser and super().has_module_permission(request)

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser and super().has_view_permission(request, obj)

    def has_add_permission(self, request):
        return request.user.is_superuser and super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser and super().has_delete_permission(request, obj)


@admin.register(User)
class UserAdmin(SuperuserAdminMixin, DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Viddie", {"fields": ("is_verified", "use_service_api_keys")}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        (
            "Viddie",
            {
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "is_verified",
                    "use_service_api_keys",
                )
            },
        ),
    )


@admin.register(Login)
class LoginAdmin(SuperuserAdminMixin, admin.ModelAdmin):
    list_display = ("user", "ip", "date", "count")
    readonly_fields = ("user", "ip", "date", "count")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
