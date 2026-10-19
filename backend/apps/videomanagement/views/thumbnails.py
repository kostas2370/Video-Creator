from rest_framework.decorators import action
from rest_framework.response import Response

from apps.videomanagement.services.media.thumbnails import ensure_thumbnail


class VideoThumbnailMixin:
    @action(detail=True, methods=["POST"])
    def thumbnail(self, request, pk=None):
        image = ensure_thumbnail(self.get_object())
        return Response({"thumbnail": request.build_absolute_uri(image.url)})
