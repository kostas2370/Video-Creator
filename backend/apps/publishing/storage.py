"""Upload snapshots live outside publicly served media directories."""

import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible

from apps.common.r2_storage import R2StorageMixin


@deconstructible
class PrivateExportStorage(R2StorageMixin, FileSystemStorage):
    namespace = "publishing"

    @property
    def base_location(self):
        return settings.PUBLISHING_SNAPSHOT_ROOT

    @property
    def location(self):
        return os.path.abspath(self.base_location)

    def url(self, name):
        raise ValueError(
            "Publishing snapshots are available only through signed job URLs."
        )
