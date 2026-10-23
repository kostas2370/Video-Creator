"""Load complete editor responses with a query count independent of scene count."""

from apps.videomanagement.models import Video


def load_video_detail(video_id, *, queryset=None):
    if queryset is None:
        queryset = Video.objects.all()
    return queryset.with_editor_media().get(pk=video_id)
