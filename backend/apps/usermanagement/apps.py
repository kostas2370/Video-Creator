from django.apps import AppConfig


class UsermanagementConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.usermanagement"

    def ready(self):
        from . import signals  # noqa: F401
