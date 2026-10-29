from django.db import models


class SeriesEpisodeQuerySet(models.QuerySet):
    def with_script(self):
        """Load everything needed to serialize episodes and review their memory."""
        return self.select_related("video").prefetch_related(
            "video__scenes__scene_images"
        )
