from django.db.models import OuterRef, Q, Subquery
from django_filters import rest_framework as filters

from apps.common.filters import (
    BaseFilterSet,
    OwnerFilterSet,
    OwnerOrSuperuserFilterSet,
    SearchFilterSet,
    SearchOrderingFilterSet,
)

from .models import (
    MediaAsset,
    Scene,
    SceneImage,
    Video,
    VideoType,
    VoiceModel,
)
from .serializers.models import (
    AvatarSerializer,
    IntroSerializer,
    OutroSerializer,
    TemplatePromptsSerializer,
    VoiceModelSerializer,
)
from .services.media.icons import search_icons


class MediaAssetFilter(OwnerFilterSet):
    scope = filters.ChoiceFilter(choices=[("private", "My media"), ("shared", "General music")], method="filter_scope")
    search = filters.CharFilter(method="filter_search")
    kind = filters.ChoiceFilter(
        choices=[*MediaAsset.Kind.choices, ("VISUAL", "Images and video")],
        method="filter_kind",
    )

    class Meta:
        model = MediaAsset
        fields = ("search", "kind", "scope")

    def scope_queryset(self, queryset):
        if self.request is None or not self.request.user.is_authenticated:
            return queryset.none()
        return queryset.filter(
            Q(created_by=self.request.user, is_shared=False)
            | (Q(is_shared=True, catalog_approved=True, kind="AUDIO", created_by__isnull=True)
               & ~Q(file="") & ~Q(license_url=""))
        )

    def filter_scope(self, queryset, name, value):
        return queryset.filter(is_shared=value == "shared")

    def filter_search(self, queryset, name, value):
        term = value.strip()[:100]
        return (
            queryset.filter(Q(title__icontains=term) | Q(tags__icontains=term))
            if term
            else queryset
        )

    def filter_kind(self, queryset, name, value):
        if value == "VISUAL":
            return queryset.filter(
                kind__in=(MediaAsset.Kind.IMAGE, MediaAsset.Kind.VIDEO)
            )
        return queryset.filter(kind=value)


class VideoFilter(OwnerFilterSet, SearchFilterSet):
    search_fields = ("title", "tags__tiktok", "tags__youtube", "tags__search")
    creation_mode = filters.ChoiceFilter(
        choices=[
            ("AI", "AI video"),
            ("MANUAL", "Manual edit"),
            ("STORY", "Story video"),
            ("SERIES", "Series episode"),
        ],
        method="filter_creation_mode",
    )
    is_favorite = filters.BooleanFilter()
    ordering = filters.OrderingFilter(
        fields=("updated_at", "created_at", "title"), method="filter_ordering"
    )

    class Meta:
        model = Video
        fields = ("status", "video_type", "creation_mode", "is_favorite")

    def filter_creation_mode(self, queryset, name, value):
        if value in ("STORY", "SERIES"):
            return queryset.filter(settings__creation_mode=value)
        # Older projects may have null settings or no creation_mode key.
        return queryset.filter(video_type=VideoType(value)).filter(
            Q(settings__creation_mode__isnull=True)
            | ~Q(settings__creation_mode__in=("STORY", "SERIES"))
        )

    def filter_ordering(self, queryset, name, value):
        return queryset.order_by(*value, "id")

    def scope_queryset(self, queryset):
        queryset = (
            super()
            .scope_queryset(queryset)
            .order_by("-updated_at", "-id")
            .select_related("music", "prompt")
        )
        if self.action == "list":
            queryset = queryset.listable().annotate(
                scene_preview=Subquery(
                    SceneImage.objects.filter(
                        scene__video_id=OuterRef("pk"), scene__archived_at__isnull=True
                    )
                    .exclude(asset__file="")
                    .exclude(asset__file__isnull=True)
                    .order_by("scene__position", "created_at", "id")
                    .values("asset__file")[:1]
                )
            )

        if self.action in ("retrieve", "preview"):
            queryset = queryset.with_editor_media()

        return queryset


class VoiceFilter(SearchOrderingFilterSet):
    search_fields = ("name",)
    serializer_class = VoiceModelSerializer

    class Meta:
        model = VoiceModel
        fields = ("is_cloned",)

    def scope_queryset(self, queryset):
        if self.action == "destroy":
            queryset = queryset.filter(created_by=self.request.user)
        elif self.action in ("preview", "refresh"):
            queryset = queryset.filter(created_by=self.request.user, is_cloned=True)
        else:
            queryset = queryset.available_to(self.request.user)
        return queryset.order_by("id")


class TemplatePromptFilter(OwnerOrSuperuserFilterSet, SearchOrderingFilterSet):
    search_fields = ("title",)
    serializer_class = TemplatePromptsSerializer


class AvatarFilter(OwnerFilterSet, SearchOrderingFilterSet):
    search_fields = ("name",)
    serializer_class = AvatarSerializer


class IntroFilter(OwnerOrSuperuserFilterSet, SearchOrderingFilterSet):
    search_fields = ("name",)
    serializer_class = IntroSerializer


class OutroFilter(OwnerOrSuperuserFilterSet, SearchOrderingFilterSet):
    search_fields = ("name",)
    serializer_class = OutroSerializer


class SceneFilter(BaseFilterSet):
    def scope_queryset(self, queryset):
        if self.action == "restore":
            queryset = Scene.all_objects.all()
        return queryset.select_related("video")


class CaptionProjectFilter(OwnerFilterSet):
    def scope_queryset(self, queryset):
        queryset = super().scope_queryset(queryset)
        if self.action == "list":
            queryset = queryset.defer("words", "style")
        return queryset


class IconFilter(BaseFilterSet):
    def scope_queryset(self, queryset):
        params = self.data or {}
        keys = params.get("keys")
        icons = search_icons(
            params.get("search", "")[:300],
            keys=keys[:3000].split(",")[:24] if keys is not None else None,
            user=self.request.user,
            queryset=queryset,
        )
        if params.get("mine") == "true":
            icons = icons.filter(created_by=self.request.user)
        return icons
