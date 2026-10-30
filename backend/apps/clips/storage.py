from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible
from django.utils.functional import cached_property


@deconstructible
class ClipStorage(FileSystemStorage):
    def _clear_cached_properties(self, setting, **kwargs):
        if setting == "CLIP_STORAGE_ROOT":
            self.__dict__.pop("base_location", None)
            self.__dict__.pop("location", None)
        super()._clear_cached_properties(setting, **kwargs)

    @cached_property
    def base_location(self):
        return str(
            getattr(settings, "CLIP_STORAGE_ROOT", None)
            or Path(settings.MEDIA_ROOT) / "private-clips"
        )


clip_storage = ClipStorage()
