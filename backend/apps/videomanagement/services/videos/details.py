"""Load complete editor responses with a query count independent of scene count."""

from apps.videomanagement.models import Video


def load_video_detail(video_id, *, queryset=None):
    if queryset is None:
        queryset = Video.objects.all()
    return (
        queryset.select_related("music", "prompt", "intro", "outro")
        .prefetch_related("scenes__scene_images__asset")
        .get(pk=video_id)
    )
