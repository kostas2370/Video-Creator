import logging

from django.contrib import admin, messages
from django.utils import timezone

from .models import AccessRequest, Login, User
from .services import approve_access_request

logger = logging.getLogger(__name__)

admin.site.register(User)
admin.site.register(Login)


@admin.register(AccessRequest)
class AccessRequestAdmin(admin.ModelAdmin):
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

    def has_module_permission(self, request):
        return request.user.is_superuser and super().has_module_permission(request)

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser and super().has_view_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser and super().has_delete_permission(request, obj)

    def has_add_permission(self, request):
        return False

    @admin.action(description="Approve selected pending requests and email invitations")
    def approve_requests(self, request, queryset):
        approved = failed = 0
        for request_id in queryset.values_list("pk", flat=True):
            try:
                approved += approve_access_request(request_id, request.user)
            except Exception:
                logger.exception("Access invitation delivery failed")
                failed += 1
        self.message_user(request, f"Approved and invited {approved} request(s).")
        if failed:
            self.message_user(
                request,
                f"{failed} invitation(s) could not be sent. Those requests remain pending; check email delivery and retry.",
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
