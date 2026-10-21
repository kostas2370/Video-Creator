"""Save generated thumbnail drafts as reusable assets."""

from django.core.files.base import ContentFile

from apps.videomanagement.models import MediaAsset


def archive_generated_cover(video, image):
    return MediaAsset.from_visual(
        user=video.created_by,
        upload=ContentFile(image, name="thumbnail.png"),
        title=f"{video.title} · AI thumbnail",
        tags=["ai thumbnail"],
        kind=MediaAsset.Kind.IMAGE,
        source_video=video,
    )
