from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters

from apps.common.filters import UserFilterSet
from apps.videomanagement.models import Video


class PublishJobFilter(UserFilterSet):
    video = filters.UUIDFilter(field_name="video_id", method="filter_video")

    def filter_video(self, queryset, name, value):
        get_object_or_404(Video, pk=value, created_by=self.request.user)
        return queryset.filter(video_id=value)
