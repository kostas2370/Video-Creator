from importlib import import_module

from django.apps import AppConfig


class VideomanagementConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.videomanagement"

    def ready(self):
        import_module("apps.videomanagement.signals")
