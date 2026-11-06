from django.db.models import Count, OuterRef, Subquery

from apps.common.filters import OwnerFilterSet, SearchFilterSet

from .models import SeriesEpisode


class VideoSeriesFilter(OwnerFilterSet, SearchFilterSet):
    search_fields = ("title", "premise")

    def scope_queryset(self, queryset):
        active = SeriesEpisode.objects.filter(
            series_id=OuterRef("pk"), video__status__in=("GENERATION", "REVIEW")
        ).order_by("-number")
        queryset = (
            super()
            .scope_queryset(queryset)
            .annotate(
                episode_count=Count("episodes"),
                active_episode_id=Subquery(active.values("id")[:1]),
                active_video_id=Subquery(active.values("video_id")[:1]),
                active_episode_number=Subquery(active.values("number")[:1]),
            )
            .prefetch_related("cast_members")
            .order_by("-updated_at", "id")
        )

        return queryset
