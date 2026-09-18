from django.apps import AppConfig


class UsermanagementConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.usermanagement"

    def ready(self):
        # Imported for the @receiver side effect: without this the password-reset
        # token is created and no mail is ever sent.
        from . import signals  # noqa: F401
