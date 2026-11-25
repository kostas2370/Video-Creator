import logging

from django.contrib import admin, messages
from django.utils import timezone
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import AccessRequest, Login, User
from .tasks import send_access_invitation

logger = logging.getLogger(__name__)


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


@admin.register(AccessRequest)
class AccessRequestAdmin(SuperuserAdminMixin, admin.ModelAdmin):
    list_display = ("email", "name", "status", "created_at", "reviewed_at")
    list_filter = ("status",)
    search_fields = ("email", "name")
    readonly_fields = (
        "name",
        "email",
        "message",
        "status",
        "created_at",
        "reviewed_at",
        "reviewed_by",
    )
    actions = ("approve_requests", "reject_requests")

    def has_add_permission(self, request):
        return False

    @admin.action(
        description="Queue approval invitations for selected pending requests"
    )
    def approve_requests(self, request, queryset):
        queued = failed = 0
        for request_id in queryset.filter(
            status=AccessRequest.Status.PENDING
        ).values_list("pk", flat=True):
            try:
                send_access_invitation.delay(str(request_id), str(request.user.pk))
                queued += 1
            except Exception:
                logger.exception("Access invitation queueing failed")
                failed += 1
        self.message_user(
            request,
            f"Queued {queued} invitation(s). Requests are approved after successful email delivery.",
        )
        if failed:
            self.message_user(
                request,
                f"{failed} invitation(s) could not be queued. Those requests remain pending; check the worker queue and retry.",
                level=messages.ERROR,
            )

    @admin.action(description="Reject selected pending requests")
    def reject_requests(self, request, queryset):
        count = queryset.filter(status=AccessRequest.Status.PENDING).update(
            status=AccessRequest.Status.REJECTED,
            reviewed_at=timezone.now(),
            reviewed_by=request.user,
        )
        self.message_user(request, f"Rejected {count} request(s).")
