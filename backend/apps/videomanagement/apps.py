from importlib import import_module

from django.apps import AppConfig
from django.db.models.signals import pre_save

from apps.common.r2_storage import sync_model_files


class VideomanagementConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.videomanagement"

    def ready(self):
        import_module("apps.videomanagement.signals")
        pre_save.connect(sync_model_files, dispatch_uid="r2-sync-model-files")
