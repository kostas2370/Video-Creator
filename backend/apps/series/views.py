from django.db.models import Count, OuterRef, Subquery
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.series.models import SeriesEpisode, VideoSeries
from apps.series.serializers import (
    EpisodeDraftSerializer,
    EpisodeMemoryDraftSerializer,
    EpisodeMemorySerializer,
    SeriesEpisodeSerializer,
    VideoSeriesSerializer,
    validate_episode_generation,
)
from apps.series.services import (
    draft_episode,
    draft_episode_memory,
    retry_episode,
    update_episode_memory,
)
from apps.videomanagement.exceptions import VideoEditConflict
from apps.videomanagement.paginator import AssetResultsPagination
from apps.videomanagement.throttling import GenerateRateThrottle

from .characters import draft_cast, save_reference_image
from .models import CharacterReference
from .serializers import (
    CastDraftRequestSerializer,
    CharacterDescriptionRequestSerializer,
    CharacterReferenceRequestSerializer,
    CharacterReferenceSerializer,
)
from .tasks import generate_character_reference_task
from .throttling import (
    CharacterImageRateThrottle,
    SeriesCastDraftRateThrottle,
    SeriesMemoryRateThrottle,
)


class VideoSeriesView(viewsets.ModelViewSet):
    queryset = VideoSeries.objects.all()
    serializer_class = VideoSeriesSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = AssetResultsPagination
    filter_backends = [SearchFilter]
    search_fields = ["title", "premise"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return VideoSeries.objects.none()
        active = SeriesEpisode.objects.filter(
            series_id=OuterRef("pk"), video__status__in=("GENERATION", "REVIEW")
        ).order_by("-number")
        return (
            VideoSeries.objects.filter(created_by=self.request.user)
            .annotate(
                episode_count=Count("episodes"),
                active_episode_id=Subquery(active.values("id")[:1]),
                active_video_id=Subquery(active.values("video_id")[:1]),
                active_episode_number=Subquery(active.values("number")[:1]),
            )
            .order_by("-updated_at", "id")
        )

    def get_episode(self, episode_id):
        return get_object_or_404(
            self.get_object().episodes.with_script(), pk=episode_id
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def get_throttles(self):
        if self.action in ("cast_draft", "character_description"):
            return [SeriesCastDraftRateThrottle()]
        if self.action == "character_references" and self.request.method == "POST":
            return [CharacterImageRateThrottle()]
        if self.action == "draft_memory":
            return [SeriesMemoryRateThrottle()]
        if self.request.method == "POST" and self.action in ("episodes", "retry"):
            return [GenerateRateThrottle()]
        return super().get_throttles()

    @action(detail=False, methods=["post"])
    def cast_draft(self, request):
        serializer = CastDraftRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            {"cast": draft_cast(request.user, dict(serializer.validated_data))}
        )

    @action(detail=False, methods=["post"])
    def character_description(self, request):
        serializer = CharacterDescriptionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        choices = dict(serializer.validated_data)
        character = draft_cast(request.user, choices)[0]
        if choices["name"]:
            character["name"] = choices["name"]
        return Response(
            {
                "character": {
                    key: character[key]
                    for key in (
                        "name",
                        "appearance",
                        "wardrobe",
                        "personality",
                        "relationships",
                    )
                }
            }
        )

    @action(detail=False, methods=["get", "post"])
    def character_references(self, request):
        if request.method == "GET":
            from rest_framework import serializers

            identifier = serializers.UUIDField().run_validation(
                request.query_params.get("id")
            )
            reference = get_object_or_404(
                CharacterReference, pk=identifier, created_by=request.user
            )
            return Response(
                CharacterReferenceSerializer(
                    reference, context=self.get_serializer_context()
                ).data
            )
        serializer = CharacterReferenceRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        choices = dict(serializer.validated_data)
        image = choices.pop("image", None)
        reference = CharacterReference.objects.create(
            created_by=request.user, description=choices
        )
        if image:
            try:
                save_reference_image(reference, image)
            except Exception:
                reference.delete()
                raise
        else:
            try:
                generate_character_reference_task.delay(str(reference.pk))
            except Exception as exc:
                reference.status = "FAILED"
                reference.error = "Image generation could not be queued. Try again."
                reference.save(update_fields=["status", "error", "updated_at"])
                error = APIException(reference.error)
                error.status_code = 503
                raise error from exc
        return Response(
            CharacterReferenceSerializer(
                reference, context=self.get_serializer_context()
            ).data,
            status=201 if image else 202,
        )

    @action(detail=True, methods=["get", "post"])
    def episodes(self, request, pk=None):
        series = self.get_object()
        if request.method == "POST":
            serializer = EpisodeDraftSerializer(
                data=request.data,
                context={**self.get_serializer_context(), "series": series},
            )
            serializer.is_valid(raise_exception=True)
            episode = draft_episode(
                series, owner=request.user, **serializer.validated_data
            )
            return Response(SeriesEpisodeSerializer(episode).data, status=202)
        rows = series.episodes.with_script()
        page = self.paginate_queryset(rows)
        return self.get_paginated_response(
            SeriesEpisodeSerializer(page, many=True).data
        )

    @action(
        detail=True, methods=["patch"], url_path=r"episodes/(?P<episode_id>[0-9a-f-]+)"
    )
    def memory(self, request, pk=None, episode_id=None):
        episode = self.get_episode(episode_id)
        serializer = EpisodeMemorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        episode = update_episode_memory(
            episode,
            summary=serializer.validated_data["summary"],
            script_hash=serializer.validated_data["script_hash"],
            previous_summary=serializer.validated_data["previous_summary"],
        )
        return Response(SeriesEpisodeSerializer(episode).data)

    @action(
        detail=True,
        methods=["post"],
        url_path=r"episodes/(?P<episode_id>[0-9a-f-]+)/retry",
    )
    def retry(self, request, pk=None, episode_id=None):
        episode = self.get_episode(episode_id)
        if episode.video_id is None:
            raise ValidationError(
                "This episode's video was deleted. Draft a new episode instead."
            )
        if not episode.can_retry:
            raise VideoEditConflict(
                "Open the episode in the editor to review or resume it."
            )
        params = validate_episode_generation(
            episode.generation_params, self.get_serializer_context()
        )
        episode = retry_episode(episode, generation_params=params, owner=request.user)
        return Response(SeriesEpisodeSerializer(episode).data, status=202)

    @action(
        detail=True,
        methods=["post"],
        url_path=r"episodes/(?P<episode_id>[0-9a-f-]+)/draft_memory",
    )
    def draft_memory(self, request, pk=None, episode_id=None):
        episode = self.get_episode(episode_id)
        serializer = EpisodeMemoryDraftSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            draft_episode_memory(
                episode, owner=request.user, **serializer.validated_data
            )
        )
